# npm-dist

Source of the `dashiai-ppt-skill` npm package:

- `install.mjs` — the `npx dashiai-ppt-skill` installer bin, verbatim.
- `publish-npm-skill.mjs` — the publish script; the package is assembled from this directory's installer plus the `skills/dashiai-ppt/` content of this repository (with `project/npmrc.template` materialized as `.npmrc` at install time).

These files are synced from the development repository on every release.
