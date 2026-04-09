<#--
  Custom user profile field renderer for registration/update flows.
  Mirrors the PDP login/register standalone markup instead of the default Keycloak layout.
-->

<#macro userProfileFormFields>
    <#list profile.attributes as attribute>
        <#if attribute.name == "role">
            <@renderUserProfileAttribute attribute=attribute ; callback>
                <#nested callback, attribute>
            </@renderUserProfileAttribute>
        </#if>
    </#list>

    <#list profile.attributes as attribute>
        <#if attribute.name != "role">
            <@renderUserProfileAttribute attribute=attribute ; callback>
                <#nested callback, attribute>
            </@renderUserProfileAttribute>
        </#if>
    </#list>

    <#list (profile.html5DataAnnotations!{})?keys as key>
        <script type="module" src="${url.resourcesPath}/js/${key}.js"></script>
    </#list>
</#macro>

<#macro renderUserProfileAttribute attribute>
        <#assign inputType = attribute.annotations.inputType!'text'>
        <#if attribute.name == "role">
        <div class="title title-role">
            <#assign roleValue = ((attribute.value!'')?string)?trim>
            <#assign roleOptions = []>
            <#if attribute.validators.options?? && attribute.validators.options.options??>
                <#assign roleOptions = attribute.validators.options.options>
            <#elseif attribute.annotations.inputOptionsFromValidation?? && attribute.validators[attribute.annotations.inputOptionsFromValidation]?? && attribute.validators[attribute.annotations.inputOptionsFromValidation].options??>
                <#assign roleOptions = attribute.validators[attribute.annotations.inputOptionsFromValidation].options>
            </#if>
            <div class="role-toggle" aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>">
                <#list ["Student", "Teacher"] as preferredOption>
                    <#if roleOptions?seq_contains(preferredOption)>
                        <label class="role-option">
                            <input
                                class="role-radio"
                                type="radio"
                                name="${attribute.name}"
                                value="${preferredOption}"
                                <#if roleValue == preferredOption || (!roleValue?has_content && preferredOption == "Student")>checked</#if>
                                <#if attribute.readOnly>disabled</#if>
                            />
                            <span class="role-option-label">
                                <#if preferredOption == "Student">${msg("roleStudent")}<#else>${msg("roleTeacher")}</#if>
                            </span>
                        </label>
                    </#if>
                </#list>
            </div>
            <#if messagesPerField.existsError(attribute.name)>
                <span class="error">${messagesPerField.get(attribute.name)}</span>
            </#if>
        </div>
        <#nested "afterField", attribute>
        <#else>
        <label class="title">
            ${advancedMsg(attribute.displayName!'')}
            <#if attribute.required?? && attribute.required>
                *
            </#if>

            <#switch inputType>
                <#case 'select'>
                <#case 'multiselect'>
                    <select
                        id="${attribute.name}"
                        class="input"
                        name="${attribute.name}"
                        aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>"
                        <#if attribute.readOnly>disabled</#if>
                        <#if inputType == 'multiselect'>multiple</#if>
                        <#if attribute.annotations.inputTypeSize??>size="${attribute.annotations.inputTypeSize}"</#if>
                        <#list (attribute.html5DataAnnotations!{}) as key, value>
                            data-${key}="${value}"
                        </#list>
                    >
                        <#if inputType == 'select'>
                            <option value=""></option>
                        </#if>
                        <#if attribute.annotations.inputOptionsFromValidation?? && attribute.validators[attribute.annotations.inputOptionsFromValidation]?? && attribute.validators[attribute.annotations.inputOptionsFromValidation].options??>
                            <#assign options = attribute.validators[attribute.annotations.inputOptionsFromValidation].options>
                        <#elseif attribute.validators.options?? && attribute.validators.options.options??>
                            <#assign options = attribute.validators.options.options>
                        <#else>
                            <#assign options = []>
                        </#if>
                        <#list options as option>
                            <option value="${option}" <#if attribute.values?? && attribute.values?seq_contains(option)>selected</#if>>
                                ${option}
                            </option>
                        </#list>
                    </select>
                    <#break>

                <#case 'textarea'>
                    <textarea
                        id="${attribute.name}"
                        class="input"
                        name="${attribute.name}"
                        aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>"
                        <#if attribute.readOnly>disabled</#if>
                        <#if attribute.annotations.inputTypeCols??>cols="${attribute.annotations.inputTypeCols}"</#if>
                        <#if attribute.annotations.inputTypeRows??>rows="${attribute.annotations.inputTypeRows}"</#if>
                        <#if attribute.annotations.inputTypeMaxlength??>maxlength="${attribute.annotations.inputTypeMaxlength}"</#if>
                        <#list (attribute.html5DataAnnotations!{}) as key, value>
                            data-${key}="${value}"
                        </#list>
                    >${(attribute.value!'')}</textarea>
                    <#break>

                <#default>
                    <input
                        id="${attribute.name}"
                        class="input"
                        name="${attribute.name}"
                        type="<#if inputType?starts_with('html5-')>${inputType[6..]}<#else>${inputType}</#if>"
                        value="${(attribute.value!'')}"
                        aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>"
                        <#if attribute.readOnly>disabled</#if>
                        <#if attribute.autocomplete??>autocomplete="${attribute.autocomplete}"</#if>
                        <#if attribute.annotations.inputTypePlaceholder??>placeholder="${advancedMsg(attribute.annotations.inputTypePlaceholder)}"</#if>
                        <#if attribute.annotations.inputTypePattern??>pattern="${attribute.annotations.inputTypePattern}"</#if>
                        <#if attribute.annotations.inputTypeSize??>size="${attribute.annotations.inputTypeSize}"</#if>
                        <#if attribute.annotations.inputTypeMaxlength??>maxlength="${attribute.annotations.inputTypeMaxlength}"</#if>
                        <#if attribute.annotations.inputTypeMinlength??>minlength="${attribute.annotations.inputTypeMinlength}"</#if>
                        <#if attribute.annotations.inputTypeMax??>max="${attribute.annotations.inputTypeMax}"</#if>
                        <#if attribute.annotations.inputTypeMin??>min="${attribute.annotations.inputTypeMin}"</#if>
                        <#if attribute.annotations.inputTypeStep??>step="${attribute.annotations.inputTypeStep}"</#if>
                        <#list (attribute.html5DataAnnotations!{}) as key, value>
                            data-${key}="${value}"
                        </#list>
                    />
            </#switch>

            <#if messagesPerField.existsError(attribute.name)>
                <span class="error">${messagesPerField.get(attribute.name)}</span>
            </#if>
        </label>
        <#nested "afterField", attribute>
        </#if>
</#macro>
