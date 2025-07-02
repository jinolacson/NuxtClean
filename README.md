# NuxtClean

A small static analysis tool can help you remove detect unecessary code from your [Nuxt 3](https://nuxt.com/) (Vue 3) projects.

It looks through your codebase to find:

- 🔹 **Unused CSS classes**
- 🔹 **Unused named imports** (`import { foo } from...`)
- 🔹 **Dead exports** (such as functions that are exported but never used)
- 🔹 **Forgotten console logs** (`console.log`, `console.warn`, `console.error`)
- 🔹 **Unused variables**  
- 🔹 **Unused packages**  

---

## Why Use NuxtClean?

A clean codebase loads more quickly, is lighter to ship, and is easier to maintain. You benefit from NuxtClean:

- 🔹 **Minimize the bloat of CSS and JS**
- 🔹 **Prior to deployment, catch any forgotten debug statements.**
- 🔹 **To ensure safe refactoring, identify any dead code.**
- 🔹 ** Increase developer self-assurance and reliability**

## NuxtVuln

`NuxtVuln` is a lightweight static security scanner for Nuxt 3 and Vue 3 projects. It helps identify **common frontend security risks** before they reach production.

It scans your codebase for:

-  **Use of `eval()`** — risky due to potential remote code execution
-  **Unsafe `v-html` usage** — possible vector for XSS if not sanitized
-  **Dynamic `setTimeout` / `setInterval` with strings or variable input**
-  **Known vulnerabilities in dependencies via `npm audit`**

> Exported results are saved as a `.csv` file for easy review.

---

## Why Use These Tools?

A clean and secure codebase is:

- ✅ Faster and lighter to ship
- ✅ Safer for users and harder to exploit
- ✅ Easier to maintain and debug
- ✅ More professional and production-ready

---


## How to Use

### 1. Clone or copy the script

```
git clone https://github.com/your-username/NuxtClean

cd NuxtClean

```

### Run the code via wrapper

```
# Run the cleaning tool
python nuxt_tool.py --mode clean --path /home/jino/Documents/public/winona-marketing-nuxt3

# Run the security scanner
python nuxt_tool.py --mode vuln --path /home/jino/Documents/public/winona-marketing-nuxt3

```

### Demo
![Demo](demo.gif)

