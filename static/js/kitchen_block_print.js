(function(global) {
    'use strict';

    var qzReady = false;

    var KITCHEN_DOC_STYLES = [
        '@page { size: 80mm auto; margin: 0; }',
        'html, body { margin: 0; padding: 0; width: 72mm; background: #fff; color: #000; }',
        'body { font-family: Arial, Helvetica, sans-serif; font-size: 11px; line-height: 1.25; padding: 2mm; }',
        '.block.smallprint { width: 100%; }',
        '.thermal-header { text-align: center; margin-bottom: 6px; }',
        '.thermal-header h1, h1 { font-size: 14px; font-weight: 800; margin: 0 0 3px; text-transform: uppercase; }',
        '.thermal-header p, p { font-size: 10px; font-weight: 600; margin: 2px 0; }',
        '.thermal-divider { border: none; border-top: 1px dashed #000; margin: 4px 0; }',
        '.kitchen-item { display: flex; align-items: stretch; border: 1px solid #000; margin-bottom: 4px; }',
        '.kitchen-qty { min-width: 26px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 12px; border-right: 1px solid #000; padding: 4px 3px; }',
        '.kitchen-name-wrap { flex: 1; padding: 4px 6px; min-width: 0; }',
        '.kitchen-name { font-weight: 800; font-size: 10px; word-wrap: break-word; }'
    ].join('\n');

    function wrapKitchenDocument(blockHtml) {
        return '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>' +
            KITCHEN_DOC_STYLES + '</style></head><body>' + blockHtml + '</body></html>';
    }

    function canUseQz() {
        return typeof global.qz !== 'undefined';
    }

    function setupQzSecurity() {
        if (typeof global.configureQzSecurity === 'function') {
            global.configureQzSecurity();
        }
    }

    function ensureQzConnected() {
        if (!canUseQz()) {
            return Promise.reject(new Error('QZ Tray library not loaded'));
        }
        setupQzSecurity();
        if (global.qz.websocket.isActive()) {
            return Promise.resolve();
        }
        return global.qz.websocket.connect({ retries: 5, delay: 1 });
    }

    function resolveKitchenPrinter() {
        var configured = (global.KITCHEN_PRINTER_NAME || '').trim();
        if (configured) {
            return global.qz.printers.find(configured).catch(function() {
                return global.qz.printers.getDefault();
            });
        }
        return global.qz.printers.getDefault();
    }

    function qzPrintOneBlock(blockHtml) {
        return ensureQzConnected()
            .then(resolveKitchenPrinter)
            .then(function(printerName) {
                var config = global.qz.configs.create(printerName || null, {
                    scaleContent: true,
                    colorType: 'grayscale'
                });
                var data = [{
                    type: 'pixel',
                    format: 'html',
                    flavor: 'plain',
                    data: wrapKitchenDocument(blockHtml)
                }];
                return global.qz.print(config, data);
            });
    }

    function printHtmlBlocksViaQz(htmlBlocks) {
        return htmlBlocks.reduce(function(chain, html) {
            return chain.then(function() {
                return qzPrintOneBlock(html);
            });
        }, Promise.resolve());
    }

    function waitForIframePrintDone(printWindow) {
        return new Promise(function(resolve) {
            var settled = false;

            function finish() {
                if (settled) return;
                settled = true;
                setTimeout(resolve, 350);
            }

            if (!printWindow) {
                finish();
                return;
            }

            printWindow.addEventListener('afterprint', finish, { once: true });
            if (printWindow.matchMedia) {
                var mq = printWindow.matchMedia('print');
                var sawPrintMode = false;
                function onMqChange(event) {
                    if (event.matches) {
                        sawPrintMode = true;
                    } else if (sawPrintMode) {
                        mq.removeEventListener('change', onMqChange);
                        finish();
                    }
                }
                mq.addEventListener('change', onMqChange);
            }
            setTimeout(finish, 5000);
        });
    }

    function printHtmlBlocksViaIframe(htmlBlocks, options) {
        options = options || {};
        if (!htmlBlocks || !htmlBlocks.length) {
            return Promise.resolve();
        }

        var index = 0;

        function printNext(isFirstBlock) {
            if (index >= htmlBlocks.length) {
                return Promise.resolve();
            }

            var blockHtml = htmlBlocks[index];
            index += 1;

            return new Promise(function(resolve) {
                var iframe = document.createElement('iframe');
                iframe.setAttribute('aria-hidden', 'true');
                iframe.style.cssText = 'position:fixed;left:-9999px;top:0;width:80mm;height:200mm;border:0;opacity:0;pointer-events:none';
                document.body.appendChild(iframe);

                var printWindow = iframe.contentWindow;
                var doc = printWindow.document;
                doc.open();
                doc.write(wrapKitchenDocument(blockHtml));
                doc.close();

                function cleanupAndNext() {
                    waitForIframePrintDone(printWindow).then(function() {
                        if (iframe.parentNode) {
                            iframe.parentNode.removeChild(iframe);
                        }
                        printNext(false).then(resolve);
                    });
                }

                function doPrint() {
                    try {
                        printWindow.focus();
                        printWindow.print();
                    } catch (err) {
                        console.warn('Kitchen iframe print error:', err);
                    }
                    cleanupAndNext();
                }

                if (isFirstBlock && options.immediate) {
                    doPrint();
                } else {
                    setTimeout(doPrint, 150);
                }
            });
        }

        return printNext(true);
    }

    function printHtmlBlocksViaBrowser(htmlBlocks) {
        return printHtmlBlocksViaIframe(htmlBlocks);
    }

    function printHtmlBlocksSequentially(htmlBlocks, options) {
        options = options || {};
        if (!htmlBlocks || !htmlBlocks.length) {
            return Promise.resolve();
        }

        function browserPrint() {
            return printHtmlBlocksViaIframe(htmlBlocks);
        }

        if (options.browserOnly || !canUseQz() || global.USE_QZ_SILENT_PRINT === false) {
            return browserPrint();
        }

        return ensureQzConnected()
            .then(function() {
                qzReady = true;
                return printHtmlBlocksViaQz(htmlBlocks);
            })
            .catch(function(err) {
                console.warn('QZ Tray print unavailable, using browser print:', err);
                qzReady = false;
                return browserPrint();
            });
    }

    function printDomBlocksSequentially(blockSelector) {
        blockSelector = blockSelector || '.receipt .block.smallprint';
        var blocks = Array.prototype.slice.call(document.querySelectorAll(blockSelector));
        if (!blocks.length) {
            global.print();
            return Promise.resolve();
        }
        return printHtmlBlocksSequentially(blocks.map(function(block) {
            return block.outerHTML;
        }));
    }

    function initQz(callback) {
        if (!canUseQz()) {
            qzReady = false;
            if (callback) callback(false, 'QZ Tray scripts not loaded');
            return Promise.resolve(false);
        }
        setupQzSecurity();
        return ensureQzConnected()
            .then(function() {
                qzReady = true;
                if (callback) callback(true);
                global.dispatchEvent(new CustomEvent('kitchenPrintReady', { detail: { mode: 'qz' } }));
                return true;
            })
            .catch(function(err) {
                qzReady = false;
                var msg = (err && err.message) ? err.message : String(err);
                if (callback) {
                    callback(false, 'Browser print will be used. Start QZ Tray for silent print.');
                }
                global.dispatchEvent(new CustomEvent('kitchenPrintReady', { detail: { mode: 'browser', error: err } }));
                return false;
            });
    }

    function printSilentOrBrowser(htmlBlocks, browserFn) {
        if (!htmlBlocks || !htmlBlocks.length) {
            return;
        }

        function runBrowser() {
            if (typeof browserFn === 'function') {
                browserFn(htmlBlocks);
            } else {
                printHtmlBlocksViaIframe(htmlBlocks);
            }
        }

        if (!canUseQz() || global.USE_QZ_SILENT_PRINT === false) {
            runBrowser();
            return;
        }

        setupQzSecurity();

        var finished = false;
        function finishBrowser() {
            if (finished) return;
            finished = true;
            runBrowser();
        }

        function tryQzPrint() {
            return printHtmlBlocksViaQz(htmlBlocks).then(function() {
                finished = true;
            });
        }

        if (qzReady && global.qz.websocket.isActive()) {
            tryQzPrint().catch(function(err) {
                console.warn('QZ print failed:', err);
                finishBrowser();
            });
            return;
        }

        var connectTimeout = setTimeout(finishBrowser, 1200);

        ensureQzConnected()
            .then(function() {
                qzReady = true;
                clearTimeout(connectTimeout);
                if (finished) return;
                return tryQzPrint();
            })
            .catch(function(err) {
                console.warn('QZ not available:', err);
                clearTimeout(connectTimeout);
                finishBrowser();
            });
    }

    global.KitchenBlockPrint = {
        initQz: initQz,
        isQzAvailable: canUseQz,
        isQzReady: function() { return qzReady; },
        printHtmlBlocksSequentially: printHtmlBlocksSequentially,
        printBrowserBlocksSequentially: printHtmlBlocksViaIframe,
        printDomBlocksSequentially: printDomBlocksSequentially,
        printSilentOrBrowser: printSilentOrBrowser
    };
})(window);
