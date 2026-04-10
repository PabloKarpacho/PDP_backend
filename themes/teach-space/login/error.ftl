<#--
  Error page template for Teach-Space Keycloak theme
-->
<!DOCTYPE html>
<html class="login-pf" lang="${locale.currentLanguageTag!'en'}">
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${msg("errorTitle", (realm.displayName!''))}</title>

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
</head>
<body class="login-pf-page">

    <header class="custom-header">
        <div class="header-left">
            <img src="${url.resourcesPath}/img/logo.png" alt="Teach-Space" class="header-logo" />
            <span class="header-title">Teach-Space</span>
        </div>
        <div class="header-right"></div>
    </header>

    <main class="login-content">
        <div class="form">
            <h1 class="form-title">${msg("errorTitle")}</h1>
            <div class="error">${(message.summary!'An error occurred')?no_esc}</div>
            <#if skipLink??>
                <div class="linkRow">
                    <a href="${url.loginUrl}" class="link">${msg("backToLogin")}</a>
                </div>
            </#if>
        </div>
    </main>
</body>
</html>
