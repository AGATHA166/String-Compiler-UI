# String Processing Language – Compiler Front End (Python + HTML/CSS/JS)

| File | What it does |
|---|---|
| `compiler.py` | the compiler: lexer, parser, semantic analysis, runs the program |
| `app.py` | web server: serves the page and runs `compile_code()` for `/compile` |
| `static/index.html` | page layout |
| `static/style.css` | styling (light and dark mode) |
| `static/script.js` | sends code to the backend, shows tokens / tree / symbols / errors |
| `tests/` | sample programs |

Only Python 3 is needed. There are no packages to install.

## Run

```bash
cd string-compiler-python
python app.py          # on Linux/Mac you may need: python3 app.py
```
Open **http://localhost:8000**. Press Ctrl+C to stop.

Without the UI:
```bash
python compiler.py tests/1_valid.str
```

## How it works

```
browser (script.js) --code--> app.py --> compiler.py
                                           1. lexer()             code   -> tokens
                                           2. Parser              tokens -> syntax tree
                                           3. semantic_analysis() tree   -> symbol table
                                           4. run()               output (only if no errors)
browser <--JSON: tokens, tree, symbols, errors, output--
```

## Language

```c
string name = "Anna";          // declaration
string greet;                  // declaration without a value
greet = "Hi " + name;          // assignment + concatenation
print(greet + "!\n");          // output
```
Valid escapes: `\n` `\t` `\\` `\"`

## Grammar (parsed by recursive descent)

```
program : stmt*
stmt    : string ID ;
        | string ID = expr ;
        | ID = expr ;
        | print ( expr ) ;
expr    : term { + term }
term    : ID | STRING_LITERAL | ( expr )
```

## Errors detected

| Phase | Examples |
|---|---|
| Lexical | invalid escape `"\q"`, unterminated string `"Oops;`, unknown character `@` |
| Syntax | `string = "x";`, `print "x";`, missing `;` |
| Semantic | variable used or assigned before declaration, variable declared twice |
