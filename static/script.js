// script.js - sends the code to the Python backend and shows the results.
// All compiling happens in compiler.py; this file only displays the JSON it returns.

const EXAMPLES = {
  "Valid program":
`// declaration, concatenation, print
string name = "Anna";
string greet = "Hi " + name;
print(greet + "!");`,
  "Escape sequences":
`string x = "Line 1\\nLine 2";
string q = "She said \\"hello\\"";
string p = "C:\\\\temp\\tdone";
print(x);
print(q);
print(p);`,
  "Lexical errors":
`string a = "bad \\q escape";
string s = "Oops;
string b = "ok" @;`,
  "Syntax errors":
`string = "Err";
print "hello";
string c = "fine";
print(c)`,
  "Semantic errors":
`x = "New";
string a;
string a;
print(greet);`,
};

const codeBox = document.getElementById("code");
const gutter = document.getElementById("gutter");
const view = document.getElementById("view");

let result = null;          // last JSON from the backend
let activeTab = "output";

// Make text safe to put inside HTML
function esc(text) {
  return String(text).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ---------- talk to the backend ----------
async function compile() {
  try {
    const response = await fetch("/compile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: codeBox.value }),
    });
    result = await response.json();
  } catch (e) {
    result = null;
    view.innerHTML = `<div class="offline"><b>Can't reach the Python backend.</b><br>
      Run <span class="mono">python app.py</span> in the project folder, then open
      <span class="mono">http://localhost:8000</span>.</div>`;
    return;
  }
  showPipeline();
  showLineNumbers();
  showTabs();
  showView();
}

// ---------- phase bar ----------
function showPipeline() {
  const count = phase => result.errors.filter(e => e.phase === phase).length;
  const phases = [
    ["Lexical",  count("Lexical"),  `${result.tokens.length} tokens`],
    ["Syntax",   count("Syntax"),   `${result.tree.children.length} statements`],
    ["Semantic", count("Semantic"), `${result.symbols.length} symbols`],
  ];
  let html = phases.map(([name, n, info], i) => `
    ${i > 0 ? '<span class="arrow">→</span>' : ""}
    <div class="phase ${n ? "bad" : "ok"}">
      <b>${name}</b><span class="info">${info}</span>
      <span class="status">${n ? n + " error" + (n > 1 ? "s" : "") : "pass"}</span>
    </div>`).join("");
  const total = result.errors.length;
  html += `<span class="verdict ${total ? "bad" : "ok"}">
    ${total ? `Compilation failed · ${total} error${total > 1 ? "s" : ""}` : "Compilation successful"}</span>`;
  document.getElementById("pipeline").innerHTML = html;
}

// ---------- line numbers, red dot on lines with errors ----------
function showLineNumbers() {
  const badLines = new Set(result ? result.errors.map(e => e.line) : []);
  const lineCount = codeBox.value.split("\n").length;
  let html = "";
  for (let i = 1; i <= lineCount; i++) html += `<div class="${badLines.has(i) ? "err" : ""}">${i}</div>`;
  gutter.innerHTML = html;
  gutter.scrollTop = codeBox.scrollTop;
}

// ---------- tabs ----------
function showTabs() {
  document.querySelectorAll(".tab").forEach(tab => {
    const name = tab.dataset.tab;
    tab.classList.toggle("active", name === activeTab);
    let badge = "";
    if (result) {
      if (name === "output" && result.errors.length) badge = `<span class="count bad">${result.errors.length}</span>`;
      if (name === "tokens") badge = `<span class="count">${result.tokens.length}</span>`;
      if (name === "symbols") badge = `<span class="count">${result.symbols.length}</span>`;
    }
    tab.innerHTML = tab.textContent.replace(/\d+$/, "") + badge;
  });
}

// ---------- tab contents ----------
function showView() {
  if (activeTab === "grammar") { view.innerHTML = grammarHTML(); return; }
  if (!result) return;

  if (activeTab === "output") {
    if (result.success) {
      view.innerHTML = `<div class="success">✓ No lexical, syntax or semantic errors</div>
        <div class="label">Program output</div>
        <pre class="console">${esc(result.output) || '<span class="note">(no print statements)</span>'}</pre>`;
    } else {
      view.innerHTML = `<div class="label">Errors</div>` + result.errors.map(e => `
        <div class="error">
          <span class="phase-name">${e.phase}</span>
          <span class="line">line ${e.line}</span>
          <span class="msg">${esc(e.message)}</span>
        </div>`).join("") + `<p class="note">The program runs once all errors are fixed.</p>`;
    }
  }

  if (activeTab === "tokens") {
    view.innerHTML = `<table><tr><th>Line</th><th>Token</th><th>Lexeme</th></tr>` +
      result.tokens.map(t => `<tr><td>${t.line}</td><td class="mono ${t.type}">${t.type}</td>
        <td class="mono">${esc(t.lexeme)}</td></tr>`).join("") + `</table>`;
  }

  if (activeTab === "tree") {
    view.innerHTML = `<div class="tree"><ul>${treeHTML(result.tree)}</ul></div>`;
  }

  if (activeTab === "symbols") {
    view.innerHTML = result.symbols.length === 0 ? `<p class="note">No variables declared.</p>` :
      `<table><tr><th>Name</th><th>Type</th><th>Scope</th><th>Declared</th><th>Used</th></tr>` +
      result.symbols.map(s => `<tr><td class="mono">${esc(s.name)}</td><td class="mono">${s.type}</td>
        <td>${s.scope}</td><td>line ${s.line}</td><td>${s.used ? "yes" : "no"}</td></tr>`).join("") + `</table>`;
  }
}

// Draw one tree node and its children (recursive)
function treeHTML(node) {
  let label = "";
  if (node.kind === "DECL") label = `string ${esc(node.name)}`;
  if (node.kind === "ASSIGN") label = `${esc(node.name)} =`;
  if (node.kind === "CONCAT") label = "+";
  if (node.kind === "ID") label = esc(node.name);
  if (node.kind === "STR") label = esc(node.text);
  const children = node.children.map(treeHTML).join("");
  return `<li><span class="node ${node.kind}">${node.kind}</span>${label}
          ${children ? `<ul>${children}</ul>` : ""}</li>`;
}

function grammarHTML() {
  return `<div class="label">Grammar</div>
<pre class="ref">program : stmt*
stmt    : string ID ;
        | string ID = expr ;
        | ID = expr ;
        | print ( expr ) ;
expr    : term { + term }
term    : ID | STRING_LITERAL | ( expr )</pre>
<div class="label">Valid escape sequences</div>
<pre class="ref">\\n  newline    \\t  tab    \\\\  backslash    \\"  double quote</pre>
<div class="label">What each phase checks</div>
<pre class="ref">Lexical  : invalid escapes, unterminated strings, unknown characters
Syntax   : statement structure, missing ; ( ) or names
Semantic : variables declared once, and before they are used</pre>`;
}

// ---------- buttons and typing ----------
const examples = document.getElementById("examples");
for (const name in EXAMPLES) {
  const chip = document.createElement("button");
  chip.className = "chip";
  chip.textContent = name;
  chip.onclick = () => {
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    codeBox.value = EXAMPLES[name];
    activeTab = "output";
    compile();
  };
  examples.appendChild(chip);
}

document.querySelectorAll(".tab").forEach(tab => {
  tab.onclick = () => { activeTab = tab.dataset.tab; showTabs(); showView(); };
});

document.getElementById("compile").onclick = compile;

let timer;
codeBox.addEventListener("input", () => {
  showLineNumbers();
  if (document.getElementById("auto").checked) {
    clearTimeout(timer);
    timer = setTimeout(compile, 300);       // wait until typing pauses
  }
});
codeBox.addEventListener("scroll", () => { gutter.scrollTop = codeBox.scrollTop; });

// Start with the first example loaded
examples.querySelector(".chip").click();
