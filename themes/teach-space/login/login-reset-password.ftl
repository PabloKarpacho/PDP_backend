<#--
  Reset password page template for Teach-Space Keycloak theme
  Mirrors the custom login page layout.
-->
<!DOCTYPE html>
<html class="login-pf" lang="${locale.currentLanguageTag!'en'}">
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${msg("emailForgotTitle")}</title>

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
                                <a class="lang-item" href="${url.loginResetCredentialsUrl}&kc_locale=${l.languageTag}">
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
        <form id="kc-reset-password-form" class="form" action="${url.loginAction}" method="post">
            <h1 class="form-title">${msg("emailForgotTitle")}</h1>

            <div class="helper-text">
                ${msg("emailInstruction")}
            </div>

            <label class="title">
                <#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if>
                <input
                    type="text"
                    id="username"
                    class="input"
                    name="username"
                    value="${(auth.attemptedUsername!'')}"
                    autofocus
                    autocomplete="username"
                    aria-invalid="<#if messagesPerField.existsError('username')>true</#if>"
                />
                <#if messagesPerField.existsError('username')>
                    <span class="error">${messagesPerField.get('username')}</span>
                </#if>
            </label>

            <#if message??>
                <div class="error">${message.summary}</div>
            </#if>

            <button type="submit" class="submit">${msg("doSubmit")}</button>

            <div class="linkRow">
                <a href="${url.loginUrl}" class="link">${msg("backToLogin")}</a>
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
