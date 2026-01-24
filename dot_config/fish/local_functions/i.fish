function i -d "Open IntelliJ IDEA with worktree-aware project name" -a path
    set --local dir (test -n "$path" && realpath "$path" || pwd)
    set --local project_name (basename "$dir")
    set --local bare_root (git rev-parse --git-common-dir 2>/dev/null)

    if test -n "$bare_root" -a "$bare_root" != ".git" -a -d "$bare_root"
        set project_name (basename "$bare_root"):(basename "$dir")
    end

    mkdir -p "$dir/.idea"
    echo "$project_name" >"$dir/.idea/.name"

    printf '<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="VcsDirectoryMappings">
    <mapping directory="" vcs="Git" />
  </component>
</project>
' >"$dir/.idea/vcs.xml"

    set --local excludes ""
    for folder in .tox .venv node_modules .lintrunner .cache .ruff_cache .mypy_cache .pytest_cache __pycache__ build target
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
<module type="JAVA_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$">
%b%b    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
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

    idea "$dir" &
end
