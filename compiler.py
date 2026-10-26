"""
compiler.py - Compiler front end for the String Processing Language

    Phase 1  Lexer     : source code  -> tokens        (validates strings + escapes)
    Phase 2  Parser    : tokens       -> syntax tree   (recursive descent)
    Phase 3  Semantic  : syntax tree  -> symbol table  (declaration checks)
    Then, if there are no errors, the program is run and its output collected.

Grammar
    program : stmt*
    stmt    : 'string' ID ';'
            | 'string' ID '=' expr ';'
            | ID '=' expr ';'
            | 'print' '(' expr ')' ';'
    expr    : term ('+' term)*
    term    : ID | STRING_LITERAL | '(' expr ')'
"""

KEYWORDS = {"string": "KEYWORD_STRING", "print": "KEYWORD_PRINT"}
SYMBOLS = {"+": "OP_CONCAT", "=": "OP_ASSIGN", ";": "SEMICOLON", "(": "LPAREN", ")": "RPAREN"}
ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


class CompileError(Exception):
    """Raised by the parser; caught to do error recovery."""


# ---------------------------------------------------------------- Phase 1: Lexer

def lexer(code, errors):
    tokens = []
    i, line = 0, 1

    while i < len(code):
        ch = code[i]

        if ch == "\n":                                   # new line
            line += 1
            i += 1
        elif ch in " \t\r":                              # whitespace
            i += 1
        elif code.startswith("//", i):                   # comment
            while i < len(code) and code[i] != "\n":
                i += 1

        elif ch.isalpha() or ch == "_":                  # identifier or keyword
            start = i
            while i < len(code) and (code[i].isalnum() or code[i] == "_"):
                i += 1
            word = code[start:i]
            tokens.append({"type": KEYWORDS.get(word, "IDENTIFIER"), "lexeme": word, "line": line})

        elif ch == '"':                                  # string literal
            start = i
            i += 1
            value = ""
            closed = False
            while i < len(code) and code[i] != "\n":
                if code[i] == '"':
                    closed = True
                    i += 1
                    break
                if code[i] == "\\":                      # escape sequence
                    nxt = code[i + 1] if i + 1 < len(code) else ""
                    if nxt in ("", "\n"):                # backslash at end of line
                        i += 1
                        break
                    if nxt in ESCAPES:
                        value += ESCAPES[nxt]
                    else:
                        errors.append(("Lexical", line, f"invalid escape sequence '\\{nxt}' (allowed: \\n \\t \\\\ \\\")"))
                    i += 2
                    continue
                if code[i] == ";" and '"' not in code[i:].split("\n")[0]:
                    break                                # unterminated: leave ';' for the parser
                value += code[i]
                i += 1
            lexeme = code[start:i]
            if not closed:
                errors.append(("Lexical", line, f"unterminated string {lexeme} (missing closing \")"))
            tokens.append({"type": "STRING_LITERAL", "lexeme": lexeme, "value": value, "line": line})

        elif ch in SYMBOLS:                              # + = ; ( )
            tokens.append({"type": SYMBOLS[ch], "lexeme": ch, "line": line})
            i += 1

        else:
            errors.append(("Lexical", line, f"unknown character '{ch}'"))
            i += 1

    tokens.append({"type": "EOF", "lexeme": "end of file", "line": line})
    return tokens


# ---------------------------------------------------------------- Phase 2: Parser

class Parser:
    def __init__(self, tokens, errors):
        self.tokens = tokens
        self.pos = 0
        self.errors = errors

    def peek(self):
        return self.tokens[self.pos]

    def expect(self, token_type, description):
        tok = self.peek()
        if tok["type"] != token_type:
            raise CompileError(tok["line"], f"expected {description} but found '{tok['lexeme']}'")
        self.pos += 1
        return tok

    def parse_program(self):
        statements = []
        while self.peek()["type"] != "EOF":
            try:
                statements.append(self.parse_statement())
            except CompileError as e:
                self.errors.append(("Syntax", e.args[0], e.args[1]))
                # error recovery: skip to the next ';'
                while self.peek()["type"] not in ("SEMICOLON", "EOF"):
                    self.pos += 1
                if self.peek()["type"] == "SEMICOLON":
                    self.pos += 1
        return {"kind": "PROGRAM", "children": statements}

    def parse_statement(self):
        tok = self.peek()

        if tok["type"] == "KEYWORD_STRING":              # string x;   string x = expr;
            self.pos += 1
            name = self.expect("IDENTIFIER", "a variable name")
            expr = None
            if self.peek()["type"] == "OP_ASSIGN":
                self.pos += 1
                expr = self.parse_expr()
            self.expect("SEMICOLON", "';'")
            return {"kind": "DECL", "name": name["lexeme"], "line": name["line"], "children": [expr] if expr else []}

        if tok["type"] == "IDENTIFIER":                  # x = expr;
            self.pos += 1
            self.expect("OP_ASSIGN", "'='")
            expr = self.parse_expr()
            self.expect("SEMICOLON", "';'")
            return {"kind": "ASSIGN", "name": tok["lexeme"], "line": tok["line"], "children": [expr]}

        if tok["type"] == "KEYWORD_PRINT":               # print(expr);
            self.pos += 1
            self.expect("LPAREN", "'('")
            expr = self.parse_expr()
            self.expect("RPAREN", "')'")
            self.expect("SEMICOLON", "';'")
            return {"kind": "PRINT", "line": tok["line"], "children": [expr]}

        raise CompileError(tok["line"], f"a statement cannot start with '{tok['lexeme']}'")

    def parse_expr(self):                                # term + term + ...
        left = self.parse_term()
        while self.peek()["type"] == "OP_CONCAT":
            self.pos += 1
            right = self.parse_term()
            left = {"kind": "CONCAT", "children": [left, right]}
        return left

    def parse_term(self):
        tok = self.peek()
        if tok["type"] == "IDENTIFIER":
            self.pos += 1
            return {"kind": "ID", "name": tok["lexeme"], "line": tok["line"], "children": []}
        if tok["type"] == "STRING_LITERAL":
            self.pos += 1
            return {"kind": "STR", "text": tok["lexeme"], "value": tok["value"], "children": []}
        if tok["type"] == "LPAREN":
            self.pos += 1
            expr = self.parse_expr()
            self.expect("RPAREN", "')'")
            return expr
        raise CompileError(tok["line"], f"expected a variable or a string but found '{tok['lexeme']}'")


# ---------------------------------------------------------------- Phase 3: Semantic analysis

def semantic_analysis(tree, errors):
    symbols = {}      # name -> {"type", "scope", "line", "used"}

    def check_expr(node):
        if node["kind"] == "ID":
            if node["name"] not in symbols:
                errors.append(("Semantic", node["line"], f"variable '{node['name']}' is used but not declared"))
            else:
                symbols[node["name"]]["used"] = True
        for child in node["children"]:
            check_expr(child)

    for stmt in tree["children"]:
        for child in stmt["children"]:
            check_expr(child)
        if stmt["kind"] == "DECL":
            if stmt["name"] in symbols:
                first = symbols[stmt["name"]]["line"]
                errors.append(("Semantic", stmt["line"], f"variable '{stmt['name']}' is already declared (line {first})"))
            else:
                symbols[stmt["name"]] = {"type": "STRING", "scope": "Global", "line": stmt["line"], "used": False}
        elif stmt["kind"] == "ASSIGN" and stmt["name"] not in symbols:
            errors.append(("Semantic", stmt["line"], f"variable '{stmt['name']}' is assigned but not declared"))

    return symbols


# ---------------------------------------------------------------- Run the program

def run(tree):
    values, output = {}, []

    def evaluate(node):
        if node["kind"] == "STR":
            return node["value"]
        if node["kind"] == "ID":
            return values.get(node["name"], "")
        return evaluate(node["children"][0]) + evaluate(node["children"][1])   # CONCAT

    for stmt in tree["children"]:
        if stmt["kind"] == "PRINT":
            output.append(evaluate(stmt["children"][0]))
        else:
            values[stmt["name"]] = evaluate(stmt["children"][0]) if stmt["children"] else ""
    return "\n".join(output)


# ---------------------------------------------------------------- All phases together

def compile_code(code):
    errors = []
    tokens = lexer(code, errors)
    tree = Parser(tokens, errors).parse_program()
    symbols = semantic_analysis(tree, errors)
    errors.sort(key=lambda e: e[1])                    # order by line number

    return {
        "tokens": [t for t in tokens if t["type"] != "EOF"],
        "tree": tree,
        "symbols": [{"name": n, **info} for n, info in symbols.items()],
        "errors": [{"phase": p, "line": l, "message": m} for p, l, m in errors],
        "success": not errors,
        "output": run(tree) if not errors else "",
    }


# ---------------------------------------------------------------- Command line use

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("usage: python compiler.py program.str")
    result = compile_code(open(sys.argv[1], encoding="utf-8").read())

    print("TOKENS")
    for t in result["tokens"]:
        print(f"  {t['line']:<4} {t['type']:<16} {t['lexeme']}")
    print("\nSYMBOL TABLE")
    for s in result["symbols"]:
        print(f"  {s['name']:<10} {s['type']:<8} {s['scope']:<8} line {s['line']}")
    print("\nERRORS" if result["errors"] else "\nNo errors - compilation successful")
    for e in result["errors"]:
        print(f"  {e['phase']} error (line {e['line']}): {e['message']}")
    if result["success"]:
        print("\nOUTPUT\n" + result["output"])
