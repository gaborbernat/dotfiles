function p -d "Open PyCharm with worktree-aware project name and auto-config" -a path
    set --local dir (test -n "$path" && realpath "$path" || pwd)
    set --local project_name (basename "$dir")
    set --local bare_root (git rev-parse --git-common-dir 2>/dev/null)

    if test -n "$bare_root" -a "$bare_root" != ".git" -a -d "$bare_root"
        set project_name (basename "$bare_root"):(basename "$dir")
    end

    mkdir -p "$dir/.idea/inspectionProfiles"
    echo "$project_name" >"$dir/.idea/.name"

    set --local python_sdk ""
    set --local sdk_path ""
    set --local dir_tilde (string replace "$HOME" "~" "$dir")
    if test -d "$dir/.tox/dev"
        set sdk_path "$dir_tilde/.tox/dev"
        set python_sdk "Python 3.14 $sdk_path"
    else if test -d "$dir/.venv"
        set sdk_path "$dir_tilde/.venv"
        set python_sdk "Python 3.14 $sdk_path"
    end

    set --local py_versions "3.14"
    if test -f "$dir/pyproject.toml"
        set --local requires (grep -E "requires-python|python_requires" "$dir/pyproject.toml" | head -1)
        if string match -q "*3.12*" "$requires"
            set py_versions "3.12" "3.13" "3.14"
        else if string match -q "*3.13*" "$requires"
            set py_versions "3.13" "3.14"
        end
    end

    if test -n "$python_sdk"
        printf '<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectRootManager" version="2" project-jdk-name="%s" project-jdk-type="Python SDK" />
  <component name="RuffConfiguration">
    <option name="enabled" value="true" />
  </component>
  <component name="TyConfiguration">
    <option name="enabled" value="true" />
  </component>
</project>
' "$python_sdk" >"$dir/.idea/misc.xml"
    end

    printf '<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="VcsDirectoryMappings">
    <mapping directory="" vcs="Git" />
  </component>
</project>
' >"$dir/.idea/vcs.xml"

    set --local excludes ""
    for folder in .tox .venv node_modules .lintrunner .cache .ruff_cache .mypy_cache .pytest_cache __pycache__
        if test -d "$dir/$folder"
            set excludes $excludes"      <excludeFolder url=\"file://\$MODULE_DIR\$/$folder\" />\n"
        end
    end
    if test -e "$dir/CLAUDE.md"
        set excludes $excludes"      <excludeFolder url=\"file://\$MODULE_DIR\$/CLAUDE.md\" />\n"
    end

    set --local sources ""
    if test -d "$dir/src"
        set sources $sources"      <sourceFolder url=\"file://\$MODULE_DIR\$/src\" isTestSource=\"false\" />\n"
    end
    if test -d "$dir/tests"
        set sources $sources"      <sourceFolder url=\"file://\$MODULE_DIR\$/tests\" isTestSource=\"true\" />\n"
    end

    printf '<?xml version="1.0" encoding="UTF-8"?>
<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$">
%b%b    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
  <component name="TestRunnerService">
    <option name="PROJECT_TEST_RUNNER" value="py.test" />
  </component>
</module>
' "$sources" "$excludes" >"$dir/.idea/$project_name.iml"

    printf '<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectModuleManager">
    <modules>
      <module fileurl="file://$PROJECT_DIR$/.idea/%s.iml" filepath="$PROJECT_DIR$/.idea/%s.iml" />
    </modules>
  </component>
</project>
' "$project_name" "$project_name" >"$dir/.idea/modules.xml"

    set --local version_items ""
    set --local idx 0
    for v in $py_versions
        set version_items $version_items"            <item index=\"$idx\" class=\"java.lang.String\" itemvalue=\"$v\" />\n"
        set idx (math $idx + 1)
    end

    printf '<component name="InspectionProjectProfileManager">
  <profile version="1.0">
    <option name="myName" value="Project Default" />
    <inspection_tool class="PyCompatibilityInspection" enabled="true" level="WARNING" enabled_by_default="true">
      <option name="ourVersions">
        <value>
          <list size="%d">
%b          </list>
        </value>
      </option>
    </inspection_tool>
    <inspection_tool class="PyMethodParametersInspection" enabled="false" level="WEAK WARNING" enabled_by_default="false" />
    <inspection_tool class="PyNestedDecoratorsInspection" enabled="false" level="WEAK WARNING" enabled_by_default="false" />
    <inspection_tool class="PyTypeHintsInspection" enabled="false" level="WARNING" enabled_by_default="false" />
    <inspection_tool class="Eslint" enabled="true" level="WARNING" enabled_by_default="true" />
  </profile>
</component>
' (count $py_versions) "$version_items" >"$dir/.idea/inspectionProfiles/Project_Default.xml"

    printf '<component name="InspectionProjectProfileManager">
  <settings>
    <option name="PROJECT_PROFILE" value="Project Default" />
    <version value="1.0" />
  </settings>
</component>
' >"$dir/.idea/inspectionProfiles/profiles_settings.xml"

    pycharm "$dir" &
end
