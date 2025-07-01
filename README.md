# NuxtClean

A small static analysis tool can help you remove detect unecessary code from your [Nuxt 3](https://nuxt.com/) (Vue 3) projects.

It looks through your codebase to find:

- 🔹 **Unused CSS classes**
- 🔹 **Unused named imports** (`import { foo } from...`)
- 🔹 **Dead exports** (such as functions that are exported but never used)
- 🔹 **Forgotten console logs** (`console.log`, `console.warn`, `console.error`)

---

## Why Use NuxtClean?

A clean codebase loads more quickly, is lighter to ship, and is easier to maintain. You benefit from NuxtClean:

- 🔹 **Minimize the bloat of CSS and JS**
- 🔹 **Prior to deployment, catch any forgotten debug statements.**
- 🔹 **To ensure safe refactoring, identify any dead code.**
- 🔹 ** Increase developer self-assurance and reliability**

## How to Use

### 1. Clone or copy the script

```
git clone https://github.com/your-username/NuxtClean
cd NuxtClean && python nuxt_clean.py --path /path/to/your/nuxt-project
```
