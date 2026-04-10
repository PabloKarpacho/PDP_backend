<#--
  Registration page for realms using declarative user profile.
  Mirrors the custom login/register layout instead of the default Keycloak template.
-->
<#import "user-profile-commons.ftl" as userProfileCommons>
<!DOCTYPE html>
<html class="login-pf" lang="${locale.currentLanguageTag!'en'}">
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${msg("registerTitle")}</title>

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>

    <#if properties.favicons?has_content>
        <#list properties.favicons?split(' ') as favicon>
            <link href="${url.resourcesPath}/${favicon?split('==')[1]}" rel="icon" type="${favicon?split('==')[2]}"/>
        </#list>
    </#if>

    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet"/>
        </#list>
    </#if>

    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
            <script src="${url.resourcesPath}/${script}" type="text/javascript"></script>
        </#list>
    </#if>
</head>
<body class="login-pf-page">

    <header class="custom-header">
        <div class="header-left">
            <img src="${url.resourcesPath}/img/logo.png" alt="Teach-Space" class="header-logo" />
            <span class="header-title">Teach-Space</span>
        </div>
        <div class="header-right">
            <#if (locale.supported!'')?has_content && locale.supported?size gt 1>
                <div class="language-dropdown">
                    <button class="lang-btn" id="langDropdown" type="button" onclick="toggleLangMenu()">
                        <#assign currentLang = locale.supported?filter(l -> l.languageTag == locale.currentLanguageTag)?first>
                        ${currentLang.label!locale.currentLanguageTag}
                        <svg class="lang-arrow" viewBox="0 0 10 6" fill="none">
                            <path d="M1 1L5 5L9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        </svg>
                    </button>
                    <button class="lang-btn-mobile" id="langDropdownMobile" type="button" onclick="toggleLangMenu()">
                        <svg class="lang-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M2 12h20"/>
                            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                        </svg>
                    </button>
                    <div class="lang-menu-overlay" id="langMenuOverlay" onclick="closeLangMenu()"></div>
                    <div class="lang-menu" id="langMenu">
                        <#list locale.supported as l>
                            <#if l.languageTag != locale.currentLanguageTag>
                                <a class="lang-item" href="${url.registrationUrl}&kc_locale=${l.languageTag}">
                                    ${l.label!l.languageTag}
                                </a>
                            </#if>
                        </#list>
                    </div>
                </div>
            </#if>
        </div>
    </header>

    <main class="login-content">
        <form id="kc-register-form" class="form" action="${url.registrationAction}" method="post">
            <h1 class="form-title">${msg("registerTitle")}</h1>

            <@userProfileCommons.userProfileFormFields; callback, attribute>
                <#if callback == "afterField" && attribute.name == "email" && passwordRequired??>
                    <label class="title">
                        ${msg("password")}
                        <input
                            type="password"
                            id="password"
                            class="input"
                            name="password"
                            autocomplete="new-password"
                            aria-invalid="<#if messagesPerField.existsError('password','password-confirm')>true</#if>"
                        />
                        <#if messagesPerField.existsError('password')>
                            <span class="error">${messagesPerField.get('password')}</span>
                        </#if>
                    </label>

                    <label class="title">
                        ${msg("passwordConfirm")}
                        <input
                            type="password"
                            id="password-confirm"
                            class="input"
                            name="password-confirm"
                            autocomplete="new-password"
                            aria-invalid="<#if messagesPerField.existsError('password-confirm')>true</#if>"
                        />
                        <#if messagesPerField.existsError('password-confirm')>
                            <span class="error">${messagesPerField.get('password-confirm')}</span>
                        </#if>
                    </label>
                </#if>
            </@userProfileCommons.userProfileFormFields>

            <#if recaptchaRequired??>
                <div class="recaptcha">
                    <div class="g-recaptcha" data-size="compact" data-sitekey="${recaptchaSiteKey}" data-action="registration"></div>
                </div>
            </#if>

            <#if message??>
                <div class="error">${message.summary!message}</div>
            </#if>

            <button type="submit" class="submit">${msg("doRegister")}</button>

            <div class="linkRow">
                <span class="linkText">${msg("haveAccount")}</span>
                <a href="${url.loginUrl}" class="link">${msg("doLogIn")}</a>
            </div>
        </form>
    </main>

    <script>
        function toggleLangMenu() {
            var menu = document.getElementById('langMenu');
            var overlay = document.getElementById('langMenuOverlay');
            var btn = document.getElementById('langDropdown');
            var isOpen = menu.classList.contains('show');

            if (isOpen) {
                menu.classList.remove('show');
                overlay.classList.remove('show');
                btn.classList.remove('clicked');
            } else {
                menu.classList.add('show');
                overlay.classList.add('show');
                btn.classList.add('clicked');
            }
        }

        function closeLangMenu() {
            var menu = document.getElementById('langMenu');
            var overlay = document.getElementById('langMenuOverlay');
            var btn = document.getElementById('langDropdown');
            menu.classList.remove('show');
            overlay.classList.remove('show');
            btn.classList.remove('clicked');
        }

        document.addEventListener('click', function(e) {
            var menu = document.getElementById('langMenu');
            var overlay = document.getElementById('langMenuOverlay');
            var btn = document.getElementById('langDropdown');
            if (menu && !e.target.closest('.language-dropdown')) {
                menu.classList.remove('show');
                overlay.classList.remove('show');
                btn.classList.remove('clicked');
            }
        });
    </script>
</body>
</html>
