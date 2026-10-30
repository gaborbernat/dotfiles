function p -d "Open PyCharm with worktree-aware project name and auto-config" -a path
    set --local dir (pwd)
    if test -n "$path"
        set dir (realpath "$path" 2>/dev/null)
        if test -z "$dir"; or not test -d "$dir"
            echo "p: no such directory: $path" >&2
            return 1
        end
    end
    if not command -q pycharm
        echo "p: PyCharm launcher 'pycharm' not found" >&2
        return 127
    end

    _idea_project "$dir" PYTHON_MODULE '  <component name="TestRunnerService">
    <option name="PROJECT_TEST_RUNNER" value="py.test" />
  </component>
'
    mkdir -p "$dir/.idea/inspectionProfiles"

    set --local python_sdk ""
    for venv in .tox/dev .venv
        if test -d "$dir/$venv"
            set --local py_ver (string replace -rf '^version = (.+)$' '$1' <"$dir/$venv/pyvenv.cfg" 2>/dev/null)
            test -z "$py_ver" && set py_ver 3
            set python_sdk "Python $py_ver "(string replace "$HOME" "~" "$dir")"/$venv"
            break
        end
    end

    if test -n "$python_sdk"; and not test -e "$dir/.idea/misc.xml"
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

    set --local py_versions "3.14"
    if test -f "$dir/pyproject.toml"
        set --local requires (grep -E "requires-python|python_requires" "$dir/pyproject.toml" | head -1)
        if string match -q "*3.12*" "$requires"
            set py_versions "3.12" "3.13" "3.14"
        else if string match -q "*3.13*" "$requires"
            set py_versions "3.13" "3.14"
        end
    end

    set --local version_items ""
    set --local idx 0
    for v in $py_versions
        set version_items \
            $version_items"            <item index=\"$idx\" class=\"java.lang.String\" itemvalue=\"$v\" />\n"
        set idx (math $idx + 1)
    end

    if not test -e "$dir/.idea/inspectionProfiles/Project_Default.xml"
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
    <inspection_tool class="PyMethodParametersInspection" enabled="false" level="WEAK WARNING"
      enabled_by_default="false" />
    <inspection_tool class="PyNestedDecoratorsInspection" enabled="false" level="WEAK WARNING"
      enabled_by_default="false" />
    <inspection_tool class="PyTypeHintsInspection" enabled="false" level="WARNING" enabled_by_default="false" />
    <inspection_tool class="Eslint" enabled="true" level="WARNING" enabled_by_default="true" />
  </profile>
</component>
' (count $py_versions) "$version_items" >"$dir/.idea/inspectionProfiles/Project_Default.xml"
    end

    if not test -e "$dir/.idea/inspectionProfiles/profiles_settings.xml"
        printf '<component name="InspectionProjectProfileManager">
  <settings>
    <option name="PROJECT_PROFILE" value="Project Default" />
    <version value="1.0" />
  </settings>
</component>
' >"$dir/.idea/inspectionProfiles/profiles_settings.xml"
    end

    pycharm "$dir" &
end
