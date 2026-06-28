(function(global) {
    'use strict';

    var configured = false;

    // QZ Tray official demo certificate (pairs with demo private key below)
    var QZ_DEMO_CERTIFICATE =
        '-----BEGIN CERTIFICATE-----\n' +
        'MIIE9TCCAt2gAwIBAgIQNzkyMDI0MTIyMDE5MDI0NDANBgkqhkiG9w0BAQsFADCB\n' +
        'mDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAk5ZMRswGQYDVQQKDBJRWiBJbmR1c3Ry\n' +
        'aWVzLCBMTEMxGzAZBgNVBAsMElFaIEluZHVzdHJpZXMsIExMQzEZMBcGA1UEAwwQ\n' +
        'cXppbmR1c3RyaWVzLmNvbTEnMCUGCSqGSIb3DQEJARYYc3VwcG9ydEBxemluZHVz\n' +
        'dHJpZXMuY29tMB4XDTI0MTIyMDE5MDI0NFoXDTI5MTIyMDE4NTMxOVowga4xFjAU\n' +
        'BgNVBAYMDVVuaXRlZCBTdGF0ZXMxCzAJBgNVBAgMAk5ZMRIwEAYDVQQHDAlDYW5h\n' +
        'c3RvdGExGzAZBgNVBAoMElFaIEluZHVzdHJpZXMsIExMQzEbMBkGA1UECwwSUVog\n' +
        'SW5kdXN0cmllcywgTExDMRswGQYDVQQDDBJRWiBJbmR1c3RyaWVzLCBMTEMxHDAa\n' +
        'BgkqhkiG9w0BCQEMDXN1cHBvcnRAcXouaW8wggEiMA0GCSqGSIb3DQEBAQUAA4IB\n' +
        'DwAwggEKAoIBAQC+j6ewVhtLHbY3uBNgqNB5DSz+QX9Pz5Dm46bI9vt/Q1Q6BL8I\n' +
        'dhaxT2PA1AY0fqQgkzlSrwqNCjWZcrNZRw/e54FGM8zf3azbHrQif6d7Wo1JK5oN\n' +
        'kI3jdB54YVwHIAt6i3BcLIvyOHsPnrKjlpROz72Kx1kK5g0gLDuH5RYVM9KFK+HR\n' +
        'fBc3JSfeg8nUkTqYJVzlT5AGRWPXeDWloqQqSyuB1t8DihNBReWyJHQ7a4yerLOI\n' +
        'J6N0jAlLDx9yt9UznAxnoO+7tKBfxCbNJerGfePMOwRKq0gx+r8M/FTrAoj+yc+T\n' +
        'SOYtuY/VZ79HCTP/vLgm1pGyrta1we24fVezAgMBAAGjIzAhMB8GA1UdIwQYMBaA\n' +
        'FJCmULeE1LnqX/IFhBN4ReipdVRcMA0GCSqGSIb3DQEBCwUAA4ICAQAMvfp931Zt\n' +
        'PgfqGXSrsM+GAVBxcRVm14MyldWfRr+MVaFZ6cH7c+fSs8hUt2qNPwHrnpK9eev5\n' +
        'MPUL27hjfiTPwv1ojLJ180aMO0ZAfPfnKeLO8uTzY7GiPQeGK7Qh39kX9XxEOidG\n' +
        'rMwfllZ6jJReS0ZGaX8LUXhh9RHGSYJhxgyUV7clB/dJch8Bbcd+DOxwc1POUHx1\n' +
        'wWExKkoWzHCCYNvqxLC9p1eO2Elz9J9ynDjXtCBl7lssnoSUKtahBCKgN5tYmZZK\n' +
        'NErKPQpbYk5yTEK1gybxhup8i2sGEJXZ9HRJLAl0UxB+eCu1ExWv7eGbcbIZJbeh\n' +
        'bwRf03fatsqzCQbGboLWtMQfcxHrEu+5MdZwOFx8i+c0c2WYad2MkkzGYHBVHPtY\n' +
        'o+PR61uIwJC2mNkPpX94CIFxSHyZumttyVKF4AhIPm9IMGTHaIr5M39zesQpVc7N\n' +
        'VIgxmMuePBrLyh6vKvuqD7W3S2HWA/8IUX703tdhoXhv5lNo1j0oywSrrUkCvUvJ\n' +
        'FjPS8+VUtVZNl7SVetQTexdcUwoADj6c1UwL9QWItskJ5Myesco3ZY0O+3QbgCuQ\n' +
        'SRqN5D0qdaLNMdEwh1YekUp4i1jm0jzPzia+WvJrW1k1ZafV6ep+YkMBkC1SFYFw\n' +
        '1Mdy+fYGyXlSn/Mvou//SSb0fUMIpXE9NA==\n' +
        '-----END CERTIFICATE-----\n' +
        '--START INTERMEDIATE CERT--\n' +
        '-----BEGIN CERTIFICATE-----\n' +
        'MIIFEjCCA/qgAwIBAgICEAAwDQYJKoZIhvcNAQELBQAwgawxCzAJBgNVBAYTAlVT\n' +
        'MQswCQYDVQQIDAJOWTESMBAGA1UEBwwJQ2FuYXN0b3RhMRswGQYDVQQKDBJRWiBJ\n' +
        'bmR1c3RyaWVzLCBMTEMxGzAZBgNVBAsMElFaIEluZHVzdHJpZXMsIExMQzEZMBcG\n' +
        'A1UEAwwQcXppbmR1c3RyaWVzLmNvbTEnMCUGCSqGSIb3DQEJARYYc3VwcG9ydEBx\n' +
        'emluZHVzdHJpZXMuY29tMB4XDTE1MDMwMjAwNTAxOFoXDTM1MDMwMjAwNTAxOFow\n' +
        'gZgxCzAJBgNVBAYTAlVTMQswCQYDVQQIDAJOWTEbMBkGA1UECgwSUVogSW5kdXN0\n' +
        'cmllcywgTExDMRswGQYDVQQLDBJRWiBJbmR1c3RyaWVzLCBMTEMxGTAXBgNVBAMM\n' +
        'EHF6aW5kdXN0cmllcy5jb20xJzAlBgkqhkiG9w0BCQEWGHN1cHBvcnRAcXppbmR1\n' +
        'c3RyaWVzLmNvbTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBANTDgNLU\n' +
        'iohl/rQoZ2bTMHVEk1mA020LYhgfWjO0+GsLlbg5SvWVFWkv4ZgffuVRXLHrwz1H\n' +
        'YpMyo+Zh8ksJF9ssJWCwQGO5ciM6dmoryyB0VZHGY1blewdMuxieXP7Kr6XD3GRM\n' +
        'GAhEwTxjUzI3ksuRunX4IcnRXKYkg5pjs4nLEhXtIZWDLiXPUsyUAEq1U1qdL1AH\n' +
        'EtdK/L3zLATnhPB6ZiM+HzNG4aAPynSA38fpeeZ4R0tINMpFThwNgGUsxYKsP9kh\n' +
        '0gxGl8YHL6ZzC7BC8FXIB/0Wteng0+XLAVto56Pyxt7BdxtNVuVNNXgkCi9tMqVX\n' +
        'xOk3oIvODDt0UoQUZ/umUuoMuOLekYUpZVk4utCqXXlB4mVfS5/zWB6nVxFX8Io1\n' +
        '9FOiDLTwZVtBmzmeikzb6o1QLp9F2TAvlf8+DIGDOo0DpPQUtOUyLPCh5hBaDGFE\n' +
        'ZhE56qPCBiQIc4T2klWX/80C5NZnd/tJNxjyUyk7bjdDzhzT10CGRAsqxAnsjvMD\n' +
        '2KcMf3oXN4PNgyfpbfq2ipxJ1u777Gpbzyf0xoKwH9FYigmqfRH2N2pEdiYawKrX\n' +
        '6pyXzGM4cvQ5X1Yxf2x/+xdTLdVaLnZgwrdqwFYmDejGAldXlYDl3jbBHVM1v+uY\n' +
        '5ItGTjk+3vLrxmvGy5XFVG+8fF/xaVfo5TW5AgMBAAGjUDBOMB0GA1UdDgQWBBSQ\n' +
        'plC3hNS56l/yBYQTeEXoqXVUXDAfBgNVHSMEGDAWgBQDRcZNwPqOqQvagw9BpW0S\n' +
        'BkOpXjAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAJIO8SiNr9jpLQ\n' +
        'eUsFUmbueoxyI5L+P5eV92ceVOJ2tAlBA13vzF1NWlpSlrMmQcVUE/K4D01qtr0k\n' +
        'gDs6LUHvj2XXLpyEogitbBgipkQpwCTJVfC9bWYBwEotC7Y8mVjjEV7uXAT71GKT\n' +
        'x8XlB9maf+BTZGgyoulA5pTYJ++7s/xX9gzSWCa+eXGcjguBtYYXaAjjAqFGRAvu\n' +
        'pz1yrDWcA6H94HeErJKUXBakS0Jm/V33JDuVXY+aZ8EQi2kV82aZbNdXll/R6iGw\n' +
        '2ur4rDErnHsiphBgZB71C5FD4cdfSONTsYxmPmyUb5T+KLUouxZ9B0Wh28ucc1Lp\n' +
        'rbO7BnjW\n' +
        '-----END CERTIFICATE-----\n';

    // QZ Tray official demo private key (development / localhost only)
    var QZ_DEMO_PRIVATE_KEY =
        '-----BEGIN PRIVATE KEY-----\n' +
        'MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC0z9FeMynsC8+u\n' +
        'dvX+LciZxnh5uRj4C9S6tNeeAlIGCfQYk0zUcNFCoCkTknNQd/YEiawDLNbxBqut\n' +
        'bMDZ1aarys1a0lYmUeVLCIqvzBkPJTSQsCopQQ9V8WuT252zzNzs68dVGNdCJd5J\n' +
        'NRQykpwexmnjPPv0mvj7i8XgG379TyW6P+WWV5okeUkXJ9eJS2ouDYdR2SM9BoVW\n' +
        '+FgxDu6BmXhozW5EfsnajFp7HL8kQClI0QOc79yuKl3492rH6bzFsFn2lfwWy9ic\n' +
        '7cP8EpCTeFp1tFaD+vxBhPZkeTQ1HKx6hQ5zeHIB5ySJJZ7af2W8r4eTGYzbdRW2\n' +
        '4DDHCPhZAgMBAAECggEATvofR3gtrY8TLe+ET3wMDS8l3HU/NMlmKA9pxvjYfw7F\n' +
        '8h4VBw4oOWPfzU7A07syWJUR72kckbcKMfw42G18GbnBrRQG0UIgV3/ppBQQNg9Y\n' +
        'QILSR6bFXhLPnIvm/GxVa58pOEBbdec4it2Gbvie/MpJ4hn3K8atTqKk0djwxQ+b\n' +
        'QNBWtVgTkyIqMpUTFDi5ECiVXaGWZ5AOVK2TzlLRNQ5Y7US8lmGxVWzt0GONjXSE\n' +
        'iO/eBk8A7wI3zknMx5o1uZa/hFCPQH33uKeuqU5rmphi3zS0BY7iGY9EoKu/o+BO\n' +
        'HPwLQJ3wCDA3O9APZ3gmmbHFPMFPr/mVGeAeGP/BAQKBgQDaPELRriUaanWrZpgT\n' +
        'VnKKrRSqPED3anAVgmDfzTQwuR/3oD506F3AMBzloAo3y9BXmDfe8qLn6kgdZQKy\n' +
        'SFNLz888at96oi+2mEKPpvssqiwE6F3OtEM6yv4DP9KJHaHmXaWv+/sjwjzpFNjs\n' +
        'wGThBxFvrTWRJqBYsM1XNJJ2EQKBgQDUGbTSwHKqRCYWhQ1GPCZKE98l5UtMKvUb\n' +
        'hyWWOXoyoeYbJEMfG1ynX4JeXIkl6YtBjYCqszv9PjHa1rowTZaAPJ0V70zyhTcF\n' +
        't581ii9LpiejIGrELHvJnW87QmjjStkjwGIqgKLp7Qe6CDjHI9HP1NM0uav/IQLW\n' +
        'pB6wyEz1yQKBgQCuxPut+Ax2rzM05KB9PAnWzO1zt3U/rtm8IAF8uVVGf7r+EDJ0\n' +
        'ZXJO6zj5G8WTEYHz5E86GI4ltBW0lKQoKouqdu27sMrv5trXG/CSImOcTVubQot9\n' +
        'chc1CkOKTp5IeJajafO6j817wZ4N+0gNsbYYEBUCnm/7ojdfT5ficpOoQQKBgQDB\n' +
        'PgKPmaNfGeQR1Ht5qEfCakR/RF/ML79Nq15FdmytQPBjfjBhYQ6Tt+MRkgGqtxOX\n' +
        'UBMQc2iOnGHT3puYcrhScec1GufidhjhbqDxqMrag7HNYDWmMlk+IeA7/4+Mtp8L\n' +
        'gbZuvvCvbLQDfIYueaYpUuBzQ08/jZYGdVU4/+WOcQKBgAGUN0kIB6EM1K/iZ0TN\n' +
        'jlt8P5UEV3ZCyATWFiGZRhhE2WAh8gv1jx4J26pcUs1n8sd2a1h6ZuBSqsyIlNSp\n' +
        'xtKsm3bqQFDHRrPcsBX4nanrw9DzkpH1k/I3WMSdGqkDAR3DtL7yXTJXJo2Sbrp5\n' +
        'EjzSn7DcDE1tL2En/tSVXeUY\n' +
        '-----END PRIVATE KEY-----';

    global.configureQzSecurity = function() {
        if (configured || typeof global.qz === 'undefined') {
            return false;
        }

        global.qz.security.setCertificatePromise(function(resolve) {
            resolve(QZ_DEMO_CERTIFICATE);
        });

        global.qz.security.setSignatureAlgorithm('SHA512');

        global.qz.security.setSignaturePromise(function(toSign) {
            return function(resolve, reject) {
                try {
                    if (typeof KEYUTIL === 'undefined' || typeof KJUR === 'undefined') {
                        reject('jsrsasign library not loaded');
                        return;
                    }
                    var pk = KEYUTIL.getKey(QZ_DEMO_PRIVATE_KEY);
                    var sig = new KJUR.crypto.Signature({ alg: 'SHA512withRSA' });
                    sig.init(pk);
                    sig.updateString(toSign);
                    resolve(KJUR.hextob64(sig.sign()));
                } catch (err) {
                    reject(err);
                }
            };
        });

        configured = true;
        return true;
    };
})(window);
