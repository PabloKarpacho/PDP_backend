<#--
  Login page template for Teach-Space Keycloak theme
  Custom layout with header (logo + language dropdown)
-->
<!DOCTYPE html>
<html class="login-pf" lang="${locale.currentLanguageTag!'en'}">
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${msg("loginAccountTitle")}</title>

    <#-- Keycloak required resources -->
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

    <#-- ===== Custom Header: logo left, language dropdown right ===== -->
    <header class="custom-header">
        <div class="header-left">
            <img src="${url.resourcesPath}/img/logo.png" alt="Teach-Space" class="header-logo" />
            <span class="header-title">Teach-Space</span>
        </div>
        <div class="header-right">
            <#if (locale.supported!'')?has_content && locale.supported?size gt 1>
                <div class="language-dropdown">
                    <#-- Desktop full button -->
                    <button class="lang-btn" id="langDropdown" onclick="toggleLangMenu()">
                        <#assign currentLang = locale.supported?filter(l -> l.languageTag == locale.currentLanguageTag)?first>
                        ${currentLang.label!locale.currentLanguageTag}
                        <svg class="lang-arrow" viewBox="0 0 10 6" fill="none">
                            <path d="M1 1L5 5L9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        </svg>
                    </button>
                    <#-- Mobile icon button -->
                    <button class="lang-btn-mobile" id="langDropdownMobile" onclick="toggleLangMenu()" type="button">
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
                                <a class="lang-item" href="${url.loginUrl}&kc_locale=${l.languageTag}">
                                    ${l.label!l.languageTag}
                                </a>
                            </#if>
                        </#list>
                    </div>
                </div>
            </#if>
        </div>
    </header>

    <#-- ===== Login Form Content ===== -->
    <main class="login-content">
        <form id="kc-form-login" class="form" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post">

            <#-- Title -->
            <h1 class="form-title">${msg("loginAccountTitle")}</h1>

            <#-- InputField: login (email/username) -->
            <#if !usernameHidden??>
                <label class="title">
                    <#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if>
                    <input
                        id="username"
                        class="input"
                        name="username"
                        type="text"
                        autofocus
                        autocomplete="username email"
                        value="${(login.username!'')}"
                        aria-invalid="<#if messagesPerField.existsError('username')>true</#if>"
                    />
                    <#if messagesPerField.existsError('username')>
                        <span class="error">${messagesPerField.get('username')}</span>
                    </#if>
                </label>
            </#if>

            <#-- InputField: password -->
            <label class="title">
                ${msg("password")}
                <input
                    id="password"
                    class="input"
                    name="password"
                    type="password"
                    autocomplete="current-password"
                    aria-invalid="<#if messagesPerField.existsError('password')>true</#if>"
                />
                <#if messagesPerField.existsError('password')>
                    <span class="error">${messagesPerField.get('password')}</span>
                </#if>
            </label>

            <#-- Remember me (if enabled) -->
            <#if realm.rememberMe && !usernameHidden??>
                <label class="title-remember-me title">
                    <input
                        id="rememberMe"
                        type="checkbox"
                        name="rememberMe"
                        value="true"
                        <#if login.rememberMe??>checked</#if>
                    />
                    ${msg("rememberMe")}
                </label>
            </#if>

            <#-- ErrorMessage -->
            <#if message??>
                <div class="error">${message.summary}</div>
            </#if>

            <#-- Submit button -->
            <button type="submit" class="submit" name="login" id="kc-login">${msg("doLogIn")}</button>

            <div class="links">
            <#-- Registration link -->
            <#if realm.registrationAllowed>
                <div class="linkRow">
                    <span class="linkText">${msg("noAccount")}</span>
                    <a href="${url.registrationUrl}" class="link">${msg("doRegister")}</a>
                </div>
            </#if>

            <#-- Forgot password link -->
            <#if realm.resetPasswordAllowed>
                <div class="linkRow">
                    <a href="${url.loginResetCredentialsUrl}" class="link">${msg("doForgotPassword")}</a>
                </div>
            </#if>
            </div>

        </form>

        <#-- Social providers -->
        <#if realm.password && social?? && social.providers?has_content>
            <div id="kc-social-providers" class="social-providers">
                <ul>
                    <#list social.providers as p>
                        <li>
                            <a id="social-${p.alias}" class="social-btn social-${p.providerId}" href="${p.loginUrl}">
                                <#if p.iconClasses?has_content>
                                    <i class="${p.iconClasses!''}" aria-hidden="true"></i>
                                </#if>
                                <span>${p.displayName!''}</span>
                            </a>
                        </li>
                    </#list>
                </ul>
            </div>
        </#if>
    </main>

    <script>
        // Toggle language dropdown
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

        // Close language dropdown when clicking on overlay
        function closeLangMenu() {
            var menu = document.getElementById('langMenu');
            var overlay = document.getElementById('langMenuOverlay');
            var btn = document.getElementById('langDropdown');
            menu.classList.remove('show');
            overlay.classList.remove('show');
            btn.classList.remove('clicked');
        }

        // Close language dropdown when clicking outside
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
