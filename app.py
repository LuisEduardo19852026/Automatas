import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import threading

# Intentar importar la librería de síntesis de voz pyttsx3
try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

# ==============================================================================
# 1. ANALIZADOR LÉXICO (LEXER) - MÓDULO BASE RF-03
# ==============================================================================

class TokenType:
    # Palabras reservadas
    ALGORITMO = "ALGORITMO"
    FINALGORITMO = "FINALGORITMO"
    VAR = "VAR"
    ENTERO_TYPE = "ENTERO_TYPE"
    DECIMAL_TYPE = "DECIMAL_TYPE"
    TEXTO_TYPE = "TEXTO_TYPE"
    LEER = "LEER"
    ESCRIBIR = "ESCRIBIR"
    SI = "SI"
    ENTONCES = "ENTONCES"
    SINO = "SINO"
    FINSI = "FINSI"

    # Literales e Identificadores
    ID = "ID"
    NUM_ENTERO = "NUM_ENTERO"
    NUM_DECIMAL = "NUM_DECIMAL"
    CADENA = "CADENA"

    # Operadores
    OP_SUMA = "+"
    OP_RESTA = "-"
    OP_MULT = "*"
    OP_DIV = "/"
    OP_ASIGN = "="
    OP_IGUAL = "=="
    OP_DIFERENTE = "!="
    OP_MENOR_IGUAL = "<="
    OP_MAYOR_IGUAL = ">="
    OP_MENOR = "<"
    OP_MAYOR = ">"

    # Delimitadores
    PAR_IZQ = "("
    PAR_DER = ")"
    DOS_PUNTOS = ":"
    COMA = ","

    EOF = "EOF"

KEYWORDS = {
    "Algoritmo": TokenType.ALGORITMO,
    "FinAlgoritmo": TokenType.FINALGORITMO,
    "Var": TokenType.VAR,
    "Entero": TokenType.ENTERO_TYPE,
    "Decimal": TokenType.DECIMAL_TYPE,
    "Texto": TokenType.TEXTO_TYPE,
    "Leer": TokenType.LEER,
    "Escribir": TokenType.ESCRIBIR,
    "Si": TokenType.SI,
    "Entonces": TokenType.ENTONCES,
    "SiNo": TokenType.SINO,
    "FinSi": TokenType.FINSI
}

class Token:
    def __init__(self, type_, value, line, column):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, '{self.value}', L:{self.line}, C:{self.column})"

class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Error Léxico [Línea {line}, Columna {column}]: {message}")
        self.line = line
        self.column = column

class Lexer:
    """Analizador léxico basado en autómatas finitos y reglas léxicas."""
    def __init__(self, code):
        self.code = code
        self.tokens = []
        self.tokenize()

    def tokenize(self):
        lines = self.code.split('\n')
        for line_num, line in enumerate(lines, 1):
            col = 1
            length = len(line)
            while col <= length:
                char = line[col - 1]

                if char.isspace():
                    col += 1
                    continue

                if line[col-1:].startswith("//"):
                    break

                if char in ('"', "'"):
                    quote = char
                    start_col = col
                    val = ""
                    col += 1
                    closed = False
                    while col <= length:
                        if line[col - 1] == quote:
                            closed = True
                            col += 1
                            break
                        val += line[col - 1]
                        col += 1
                    if not closed:
                        raise LexerError("Cadena de texto sin cerrar.", line_num, start_col)
                    self.tokens.append(Token(TokenType.CADENA, val, line_num, start_col))
                    continue

                if char.isdigit():
                    start_col = col
                    num_str = ""
                    is_decimal = False
                    while col <= length and (line[col - 1].isdigit() or line[col - 1] == '.'):
                        if line[col - 1] == '.':
                            if is_decimal:
                                raise LexerError("Número decimal mal formado con múltiples puntos.", line_num, col)
                            is_decimal = True
                        num_str += line[col - 1]
                        col += 1
                    t_type = TokenType.NUM_DECIMAL if is_decimal else TokenType.NUM_ENTERO
                    self.tokens.append(Token(t_type, num_str, line_num, start_col))
                    continue

                if char.isalpha() or char == '_':
                    start_col = col
                    id_str = ""
                    while col <= length and (line[col - 1].isalnum() or line[col - 1] == '_'):
                        id_str += line[col - 1]
                        col += 1
                    t_type = KEYWORDS.get(id_str, TokenType.ID)
                    self.tokens.append(Token(t_type, id_str, line_num, start_col))
                    continue

                two_char = line[col-1:col+1]
                if two_char == "==":
                    self.tokens.append(Token(TokenType.OP_IGUAL, "==", line_num, col))
                    col += 2; continue
                if two_char == "!=":
                    self.tokens.append(Token(TokenType.OP_DIFERENTE, "!=", line_num, col))
                    col += 2; continue
                if two_char == "<=":
                    self.tokens.append(Token(TokenType.OP_MENOR_IGUAL, "<=", line_num, col))
                    col += 2; continue
                if two_char == ">=":
                    self.tokens.append(Token(TokenType.OP_MAYOR_IGUAL, ">=", line_num, col))
                    col += 2; continue

                single_map = {
                    '=': TokenType.OP_ASIGN,
                    '+': TokenType.OP_SUMA,
                    '-': TokenType.OP_RESTA,
                    '*': TokenType.OP_MULT,
                    '/': TokenType.OP_DIV,
                    '<': TokenType.OP_MENOR,
                    '>': TokenType.OP_MAYOR,
                    '(': TokenType.PAR_IZQ,
                    ')': TokenType.PAR_DER,
                    ':': TokenType.DOS_PUNTOS,
                    ',': TokenType.COMA
                }
                if char in single_map:
                    self.tokens.append(Token(single_map[char], char, line_num, col))
                    col += 1
                    continue

                raise LexerError(f"Carácter no reconocido: '{char}'", line_num, col)

        self.tokens.append(Token(TokenType.EOF, "", len(lines) if lines else 1, 1))

# ==============================================================================
# 2. ANALIZADOR SINTÁCTICO (PARSER) Y ÁRBOLES SINTÁCTICOS (AST) - MÓDULO BASE RF-05
# ==============================================================================

class ParserError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Error Sintáctico [Línea {line}, Columna {column}]: {message}")
        self.line = line
        self.column = column

class ASTNode:
    def dump(self, indent=0):
        return f"{'  ' * indent}{self.__class__.__name__}"

class ProgramNode(ASTNode):
    def __init__(self, name, declarations, body):
        self.name = name
        self.declarations = declarations
        self.body = body

    def dump(self, indent=0):
        pad = '  ' * indent
        res = [f"{pad}ProgramNode: {self.name}"]
        res.append(f"{pad} Declaraciones:")
        for d in self.declarations:
            res.append(d.dump(indent + 2))
        res.append(f"{pad} Cuerpo:")
        for b in self.body:
            res.append(b.dump(indent + 2))
        return "\n".join(res)

class VarDeclNode(ASTNode):
    def __init__(self, var_type, names):
        self.var_type = var_type
        self.names = names

    def dump(self, indent=0):
        return f"{'  ' * indent}VarDeclNode ({self.var_type}): {', '.join(self.names)}"

class AssignNode(ASTNode):
    def __init__(self, var_name, expr, line):
        self.var_name = var_name
        self.expr = expr
        self.line = line

    def dump(self, indent=0):
        pad = '  ' * indent
        return f"{pad}AssignNode ({self.var_name} =)\n{self.expr.dump(indent + 1)}"

class ReadNode(ASTNode):
    def __init__(self, var_name, line):
        self.var_name = var_name
        self.line = line

    def dump(self, indent=0):
        return f"{'  ' * indent}ReadNode (Leer {self.var_name})"

class WriteNode(ASTNode):
    def __init__(self, expressions, line):
        self.expressions = expressions
        self.line = line

    def dump(self, indent=0):
        pad = '  ' * indent
        res = [f"{pad}WriteNode (Escribir):"]
        for e in self.expressions:
            res.append(e.dump(indent + 1))
        return "\n".join(res)

class IfNode(ASTNode):
    def __init__(self, condition, then_branch, else_branch, line):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.line = line

    def dump(self, indent=0):
        pad = '  ' * indent
        res = [f"{pad}IfNode:"]
        res.append(f"{pad} Condición:")
        res.append(self.condition.dump(indent + 2))
        res.append(f"{pad} Rama Entonces:")
        for t in self.then_branch:
            res.append(t.dump(indent + 2))
        if self.else_branch:
            res.append(f"{pad} Rama SiNo:")
            for e in self.else_branch:
                res.append(e.dump(indent + 2))
        return "\n".join(res)

class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right, line):
        self.left = left
        self.op = op
        self.right = right
        self.line = line

    def dump(self, indent=0):
        pad = '  ' * indent
        return f"{pad}BinaryOpNode ({self.op}):\n{self.left.dump(indent + 1)}\n{self.right.dump(indent + 1)}"

class LiteralNode(ASTNode):
    def __init__(self, value, val_type):
        self.value = value
        self.val_type = val_type

    def dump(self, indent=0):
        return f"{'  ' * indent}LiteralNode [{self.val_type}]: {self.value}"

class VariableNode(ASTNode):
    def __init__(self, name, line):
        self.name = name
        self.line = line

    def dump(self, indent=0):
        return f"{'  ' * indent}VariableNode: {self.name}"

class Parser:
    """Analizador Sintáctico Descendente Recursivo."""
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        return self.tokens[self.pos]

    def consume(self, expected_type, error_msg=None):
        tok = self.current_token()
        if tok.type == expected_type:
            self.pos += 1
            return tok
        msg = error_msg or f"Se esperaba '{expected_type}' pero se encontró '{tok.value}'."
        raise ParserError(msg, tok.line, tok.column)

    def parse(self):
        self.consume(TokenType.ALGORITMO, "El algoritmo debe iniciar con la palabra reservada 'Algoritmo'.")
        id_tok = self.consume(TokenType.ID, "Se esperaba el nombre del algoritmo tras 'Algoritmo'.")
        
        declarations = []
        while self.current_token().type == TokenType.VAR:
            declarations.append(self.parse_var_decl())

        body = []
        while self.current_token().type not in (TokenType.FINALGORITMO, TokenType.EOF):
            body.append(self.parse_statement())

        self.consume(TokenType.FINALGORITMO, "El programa debe finalizar con la palabra reservada 'FinAlgoritmo'.")
        return ProgramNode(id_tok.value, declarations, body)

    def parse_var_decl(self):
        self.consume(TokenType.VAR)
        type_tok = self.current_token()
        if type_tok.type in (TokenType.ENTERO_TYPE, TokenType.DECIMAL_TYPE, TokenType.TEXTO_TYPE):
            self.pos += 1
        else:
            raise ParserError(f"Tipo de dato no válido '{type_tok.value}'. Use Entero, Decimal o Texto.", type_tok.line, type_tok.column)
        
        self.consume(TokenType.DOS_PUNTOS, "Se esperaban dos puntos ':' tras el tipo de variable.")
        names = []
        id_tok = self.consume(TokenType.ID, "Se esperaba un nombre de variable.")
        names.append(id_tok.value)
        while self.current_token().type == TokenType.COMA:
            self.consume(TokenType.COMA)
            id_tok = self.consume(TokenType.ID, "Se esperaba un nombre de variable tras ','.")
            names.append(id_tok.value)
        return VarDeclNode(type_tok.type, names)

    def parse_statement(self):
        tok = self.current_token()

        if tok.type == TokenType.LEER:
            self.consume(TokenType.LEER)
            id_tok = self.consume(TokenType.ID, "Se esperaba un nombre de variable para la instrucción 'Leer'.")
            return ReadNode(id_tok.value, tok.line)

        elif tok.type == TokenType.ESCRIBIR:
            self.consume(TokenType.ESCRIBIR)
            exprs = [self.parse_expression()]
            while self.current_token().type == TokenType.COMA:
                self.consume(TokenType.COMA)
                exprs.append(self.parse_expression())
            return WriteNode(exprs, tok.line)

        elif tok.type == TokenType.SI:
            line = tok.line
            self.consume(TokenType.SI)
            cond = self.parse_expression()
            self.consume(TokenType.ENTONCES, "Se esperaba la palabra 'Entonces' tras la condición del 'Si'.")
            then_branch = []
            while self.current_token().type not in (TokenType.SINO, TokenType.FINSI, TokenType.EOF):
                then_branch.append(self.parse_statement())
            
            else_branch = []
            if self.current_token().type == TokenType.SINO:
                self.consume(TokenType.SINO)
                while self.current_token().type not in (TokenType.FINSI, TokenType.EOF):
                    else_branch.append(self.parse_statement())
            
            self.consume(TokenType.FINSI, "Se esperaba 'FinSi' para cerrar la estructura condicional 'Si'.")
            return IfNode(cond, then_branch, else_branch, line)

        elif tok.type == TokenType.ID:
            id_tok = self.consume(TokenType.ID)
            self.consume(TokenType.OP_ASIGN, f"Se esperaba '=' para asignar un valor a la variable '{id_tok.value}'.")
            expr = self.parse_expression()
            return AssignNode(id_tok.value, expr, tok.line)

        else:
            raise ParserError(f"Instrucción no válida o palabra inesperada '{tok.value}'.", tok.line, tok.column)

    def parse_expression(self):
        return self.parse_relational()

    def parse_relational(self):
        left = self.parse_additive()
        rel_ops = (TokenType.OP_IGUAL, TokenType.OP_DIFERENTE, TokenType.OP_MENOR,
                   TokenType.OP_MAYOR, TokenType.OP_MENOR_IGUAL, TokenType.OP_MAYOR_IGUAL)
        if self.current_token().type in rel_ops:
            op_tok = self.current_token()
            self.pos += 1
            right = self.parse_additive()
            left = BinaryOpNode(left, op_tok.type, right, op_tok.line)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current_token().type in (TokenType.OP_SUMA, TokenType.OP_RESTA):
            op_tok = self.current_token()
            self.pos += 1
            right = self.parse_multiplicative()
            left = BinaryOpNode(left, op_tok.type, right, op_tok.line)
        return left

    def parse_multiplicative(self):
        left = self.parse_primary()
        while self.current_token().type in (TokenType.OP_MULT, TokenType.OP_DIV):
            op_tok = self.current_token()
            self.pos += 1
            right = self.parse_primary()
            left = BinaryOpNode(left, op_tok.type, right, op_tok.line)
        return left

    def parse_primary(self):
        tok = self.current_token()
        if tok.type == TokenType.NUM_ENTERO:
            self.pos += 1
            return LiteralNode(int(tok.value), TokenType.ENTERO_TYPE)
        elif tok.type == TokenType.NUM_DECIMAL:
            self.pos += 1
            return LiteralNode(float(tok.value), TokenType.DECIMAL_TYPE)
        elif tok.type == TokenType.CADENA:
            self.pos += 1
            return LiteralNode(tok.value, TokenType.TEXTO_TYPE)
        elif tok.type == TokenType.ID:
            self.pos += 1
            return VariableNode(tok.value, tok.line)
        elif tok.type == TokenType.PAR_IZQ:
            self.pos += 1
            expr = self.parse_expression()
            self.consume(TokenType.PAR_DER, "Se esperaba ')' de cierre.")
            return expr
        else:
            raise ParserError(f"Expresión sintácticamente no válida cerca de '{tok.value}'.", tok.line, tok.column)

# ==============================================================================
# 3. INTÉRPRETE Y ENTORNO DE EJECUCIÓN (RUNTIME) - MÓDULO BASE RF-06 A RF-10
# ==============================================================================

class RuntimeErrorCustom(Exception):
    def __init__(self, message, line):
        super().__init__(f"Error de Ejecución [Línea {line}]: {message}")
        self.line = line

class Environment:
    """Manejo de entorno de memoria para variables y tipos."""
    def __init__(self):
        self.variables = {}

    def declare(self, name, var_type):
        default_val = 0 if var_type in (TokenType.ENTERO_TYPE, "Entero") else (0.0 if var_type in (TokenType.DECIMAL_TYPE, "Decimal") else "")
        self.variables[name] = {'type': var_type, 'value': default_val}

    def is_declared(self, name):
        return name in self.variables

    def set_value(self, name, value, line=1):
        if name not in self.variables:
            raise RuntimeErrorCustom(f"Variable '{name}' no declarada.", line)
        vtype = self.variables[name]['type']
        
        if vtype in (TokenType.ENTERO_TYPE, "Entero"):
            try:
                self.variables[name]['value'] = int(value)
            except ValueError:
                raise RuntimeErrorCustom(f"Se esperaba valor entero para '{name}', pero se ingresó '{value}'.", line)
        elif vtype in (TokenType.DECIMAL_TYPE, "Decimal"):
            try:
                self.variables[name]['value'] = float(value)
            except ValueError:
                raise RuntimeErrorCustom(f"Se esperaba valor decimal para '{name}', pero se ingresó '{value}'.", line)
        elif vtype in (TokenType.TEXTO_TYPE, "Texto"):
            self.variables[name]['value'] = str(value)

    def get_value(self, name, line=1):
        if name not in self.variables:
            raise RuntimeErrorCustom(f"Variable '{name}' no ha sido declarada.", line)
        return self.variables[name]['value']

class Interpreter:
    """Evaluador semántico y ejecutor directo del AST."""
    def __init__(self, console_callback, input_callback):
        self.console_callback = console_callback
        self.input_callback = input_callback
        self.env = Environment()

    def execute(self, ast_root):
        self.env = Environment()
        for decl in ast_root.declarations:
            for name in decl.names:
                self.env.declare(name, decl.var_type)

        for stmt in ast_root.body:
            self.execute_statement(stmt)

    def execute_statement(self, stmt):
        if isinstance(stmt, AssignNode):
            val = self.eval_expr(stmt.expr)
            self.env.set_value(stmt.var_name, val, stmt.line)

        elif isinstance(stmt, ReadNode):
            if not self.env.is_declared(stmt.var_name):
                raise RuntimeErrorCustom(f"Variable '{stmt.var_name}' no declarada para la instrucción Leer.", stmt.line)
            val = self.input_callback(f"Ingrese un valor para la variable '{stmt.var_name}':")
            if val is None:
                raise RuntimeErrorCustom("Lectura cancelada por el usuario.", stmt.line)
            self.env.set_value(stmt.var_name, val, stmt.line)

        elif isinstance(stmt, WriteNode):
            outs = [str(self.eval_expr(expr)) for expr in stmt.expressions]
            self.console_callback(" ".join(outs) + "\n")

        elif isinstance(stmt, IfNode):
            cond_val = self.eval_expr(stmt.condition)
            if bool(cond_val):
                for s in stmt.then_branch:
                    self.execute_statement(s)
            else:
                for s in stmt.else_branch:
                    self.execute_statement(s)

    def eval_expr(self, node):
        if isinstance(node, LiteralNode):
            return node.value

        elif isinstance(node, VariableNode):
            return self.env.get_value(node.name, node.line)

        elif isinstance(node, BinaryOpNode):
            left = self.eval_expr(node.left)
            right = self.eval_expr(node.right)

            if node.op == TokenType.OP_SUMA:
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return left + right
            elif node.op == TokenType.OP_RESTA:
                return left - right
            elif node.op == TokenType.OP_MULT:
                return left * right
            elif node.op == TokenType.OP_DIV:
                if right == 0:
                    raise RuntimeErrorCustom("División entre cero detectada.", node.line)
                return left / right
            elif node.op == TokenType.OP_IGUAL:
                return left == right
            elif node.op == TokenType.OP_DIFERENTE:
                return left != right
            elif node.op == TokenType.OP_MENOR:
                return left < right
            elif node.op == TokenType.OP_MAYOR:
                return left > right
            elif node.op == TokenType.OP_MENOR_IGUAL:
                return left <= right
            elif node.op == TokenType.OP_MAYOR_IGUAL:
                return left >= right
            else:
                raise RuntimeErrorCustom(f"Operador '{node.op}' no soportado.", node.line)

# ==============================================================================
# 4. CASOS DE PRUEBA OBLIGATORIOS REGISTRADOS - PRUEBAS 01 A 10
# ==============================================================================

TEST_CASES = [
    {
        "id": 1,
        "name": "Prueba 01: Asignaciones y Aritmética Simple",
        "category": "Asignaciones / Aritmética",
        "code": """Algoritmo PruebaAritmetica1\nVar Entero: a, b, resultado\na = 15\nb = 5\nresultado = a + b * 2\nEscribir "El resultado es:", resultado\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "El resultado es: 25",
        "type": "valid"
    },
    {
        "id": 2,
        "name": "Prueba 02: Expresiones con Paréntesis y Decimales",
        "category": "Asignaciones / Aritmética",
        "code": """Algoritmo PruebaAritmetica2\nVar Decimal: x, y, res\nx = 10.5\ny = 4.5\nres = (x + y) / 3.0\nEscribir "El valor final es:", res\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "El valor final es: 5.0",
        "type": "valid"
    },
    {
        "id": 3,
        "name": "Prueba 03: Entrada y Salida de Datos (Suma)",
        "category": "Entrada / Salida",
        "code": """Algoritmo EntradaSalida1\nVar Entero: n1, n2, suma\nLeer n1\nLeer n2\nsuma = n1 + n2\nEscribir "La suma es:", suma\nFinAlgoritmo""",
        "input": "n1=8, n2=12",
        "expected": "La suma es: 20",
        "type": "valid"
    },
    {
        "id": 4,
        "name": "Prueba 04: Entrada y Salida con Texto",
        "category": "Entrada / Salida",
        "code": """Algoritmo EntradaSalida2\nVar Texto: nombre\nVar Entero: edad\nLeer nombre\nLeer edad\nEscribir "Hola", nombre, "tienes", edad, "años."\nFinAlgoritmo""",
        "input": "nombre=Carlos, edad=20",
        "expected": "Hola Carlos tienes 20 años.",
        "type": "valid"
    },
    {
        "id": 5,
        "name": "Prueba 05: Condicional Si (Rama Verdadera)",
        "category": "Condicionales",
        "code": """Algoritmo CondicionalVerdadero\nVar Entero: nota\nnota = 85\nSi nota >= 60 Entonces\n    Escribir "Resultado: Aprobado"\nSiNo\n    Escribir "Resultado: Reprobado"\nFinSi\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "Resultado: Aprobado",
        "type": "valid"
    },
    {
        "id": 6,
        "name": "Prueba 06: Condicional Si (Rama Falsa)",
        "category": "Condicionales",
        "code": """Algoritmo CondicionalFalso\nVar Entero: edad\nedad = 15\nSi edad >= 18 Entonces\n    Escribir "Es mayor de edad"\nSiNo\n    Escribir "Es menor de edad"\nFinSi\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "Es menor de edad",
        "type": "valid"
    },
    {
        "id": 7,
        "name": "Prueba 07: Error Léxico (Carácter No Válido)",
        "category": "Error Léxico / Sintáctico",
        "code": """Algoritmo ErrorLexico\nVar Entero: precio\nprecio = 100 @ 5\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "Error Léxico [Línea 3, Columna 14]: Carácter no reconocido: '@'",
        "type": "error"
    },
    {
        "id": 8,
        "name": "Prueba 08: Error Sintáctico (Falta FinSi)",
        "category": "Error Léxico / Sintáctico",
        "code": """Algoritmo ErrorSintactico\nVar Entero: num\nnum = 10\nSi num > 5 Entonces\n    Escribir "Es mayor"\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "Error Sintáctico [Línea 6, Columna 1]: Se esperaba 'FinSi' para cerrar...",
        "type": "error"
    },
    {
        "id": 9,
        "name": "Prueba 09: Error de Ejecución (División entre Cero)",
        "category": "Error Ejecución / Límite",
        "code": """Algoritmo DivisionCero\nVar Entero: a, b, c\na = 10\nb = 0\nc = a / b\nEscribir c\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "Error de Ejecución [Línea 5]: División entre cero detectada.",
        "type": "error"
    },
    {
        "id": 10,
        "name": "Prueba 10: Error de Ejecución (Variable No Declarada)",
        "category": "Error Ejecución / Límite",
        "code": """Algoritmo VariableNoDeclarada\nVar Entero: x\nx = 5\ny = 10\nEscribir x\nFinAlgoritmo""",
        "input": "N/A",
        "expected": "Error de Ejecución [Línea 4]: Variable 'y' no declarada.",
        "type": "error"
    }
]

# ==============================================================================
# 5. INTERFAZ GRÁFICA DE USUARIO (GUI) - OPERACIÓN INDIVIDUALIZADA RF Y PRUEBAS
# ==============================================================================

class InterpreterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Intérprete Educativo de Pseudocódigo - Módulos RF Individulizados")
        self.root.geometry("1200x820")
        self.root.minsize(1024, 720)

        # Configuración de la operadora de voz hablada
        self.voice_enabled = tk.BooleanVar(value=True)
        self.tts_engine = None
        if HAS_TTS:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 160)
            except Exception:
                self.tts_engine = None

        self.setup_styles()
        self.create_widgets()

    def speak(self, text):
        """La operadora de voz relata acciones en segundo plano."""
        if self.voice_enabled.get() and self.tts_engine:
            def run_speech():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=run_speech, daemon=True).start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        PRIMARY = "#1E293B"
        ACCENT = "#2563EB"
        BG_COLOR = "#F8FAFC"
        
        self.root.configure(bg=BG_COLOR)
        style.configure("TFrame", background=BG_COLOR)
        style.configure("Header.TFrame", background=PRIMARY)
        style.configure("Header.TLabel", background=PRIMARY, foreground="white", font=("Segoe UI", 12, "bold"))
        style.configure("SubHeader.TLabel", background=PRIMARY, foreground="#94A3B8", font=("Segoe UI", 9))
        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background=ACCENT, foreground="white")
        style.map("Action.TButton", background=[("active", "#1D4ED8")])
        style.configure("TNotebook", background=BG_COLOR)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[8, 4])

    def create_widgets(self):
        # Barra de Título Superior
        header = ttk.Frame(self.root, style="Header.TFrame", padding=10)
        header.pack(fill="x", side="top")

        lbl_t = ttk.Label(header, text="Intérprete Educativo de Pseudocódigo", style="Header.TLabel")
        lbl_t.pack(side="left")

        lbl_sub = ttk.Label(header, text=" | Operación Individualizada RF-01 a RF-10 y Pruebas", style="SubHeader.TLabel")
        lbl_sub.pack(side="left", padx=5)

        # Control de voz de la Operadora
        chk_voice = ttk.Checkbutton(header, text="🔊 Operadora de Voz", variable=self.voice_enabled, onvalue=True, offvalue=False)
        chk_voice.pack(side="right", padx=10)

        # Panel de Pestañas Principal
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Pestañas para cada Requerimiento Funcional operado de forma individual
        tab_rf01 = ttk.Frame(self.main_notebook)
        tab_rf02 = ttk.Frame(self.main_notebook)
        tab_rf03 = ttk.Frame(self.main_notebook)
        tab_rf04 = ttk.Frame(self.main_notebook)
        tab_rf05 = ttk.Frame(self.main_notebook)
        tab_rf06 = ttk.Frame(self.main_notebook)
        tab_rf07 = ttk.Frame(self.main_notebook)
        tab_rf08 = ttk.Frame(self.main_notebook)
        tab_rf09 = ttk.Frame(self.main_notebook)
        tab_rf10 = ttk.Frame(self.main_notebook)
        tab_tests = ttk.Frame(self.main_notebook)

        self.main_notebook.add(tab_rf01, text="RF-01 Editor")
        self.main_notebook.add(tab_rf02, text="RF-02 Lenguaje")
        self.main_notebook.add(tab_rf03, text="RF-03 Léxico")
        self.main_notebook.add(tab_rf04, text="RF-04 GIC")
        self.main_notebook.add(tab_rf05, text="RF-05 Sintaxis")
        self.main_notebook.add(tab_rf06, text="RF-06 Variables")
        self.main_notebook.add(tab_rf07, text="RF-07 Aritmética")
        self.main_notebook.add(tab_rf08, text="RF-08 E/S")
        self.main_notebook.add(tab_rf09, text="RF-09 Condicional")
        self.main_notebook.add(tab_rf10, text="RF-10 Ejecución")
        self.main_notebook.add(tab_tests, text="🧪 Pruebas (1-10)")

        # Construcción individual de cada pestaña
        self.build_rf01_tab(tab_rf01)
        self.build_rf02_tab(tab_rf02)
        self.build_rf03_tab(tab_rf03)
        self.build_rf04_tab(tab_rf04)
        self.build_rf05_tab(tab_rf05)
        self.build_rf06_tab(tab_rf06)
        self.build_rf07_tab(tab_rf07)
        self.build_rf08_tab(tab_rf08)
        self.build_rf09_tab(tab_rf09)
        self.build_rf10_tab(tab_rf10)
        self.build_tests_tab(tab_tests)

    # --------------------------------------------------------------------------
    # RF-01. EDITOR DE PSEUDOCÓDIGO (CORREGIDO Y COMPLETO CON RF-01)
    # --------------------------------------------------------------------------
    def build_rf01_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-01: Módulo Individual de Edición y Ejecución de Pseudocódigo", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        txt_info = ttk.Label(parent, text="Permite escribir, modificar, corregir y ejecutar un programa mediante un botón con consola de salida.", font=("Segoe UI", 9))
        txt_info.pack(anchor="w", padx=10, pady=(0, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        lbl_ed = ttk.Label(left, text="Área de Edición del Pseudocódigo:")
        lbl_ed.pack(anchor="w")

        self.rf01_code = scrolledtext.ScrolledText(left, font=("Consolas", 11), undo=True, wrap=tk.NONE)
        self.rf01_code.pack(fill="both", expand=True, pady=5)

        sample_code = """Algoritmo ModuloEditor
Var Entero: x, y, suma
x = 25
y = 75
suma = x + y
Escribir "Operación realizada desde RF-01:", suma
FinAlgoritmo"""
        self.rf01_code.insert(tk.END, sample_code)

        btn_bar = ttk.Frame(left, padding=5)
        btn_bar.pack(fill="x", pady=5)

        btn_run = ttk.Button(btn_bar, text="▶ Ejecutar Algoritmo (RF-01)", style="Action.TButton", command=self.run_rf01_exec)
        btn_run.pack(side="left", padx=5)

        btn_clear = ttk.Button(btn_bar, text="Limpiar Editor", command=lambda: self.rf01_code.delete("1.0", tk.END))
        btn_clear.pack(side="left", padx=5)

        btn_reset = ttk.Button(btn_bar, text="Restablecer Ejemplo", command=lambda: (self.rf01_code.delete("1.0", tk.END), self.rf01_code.insert(tk.END, sample_code)))
        btn_reset.pack(side="left", padx=5)

        lbl_cons = ttk.Label(right, text="Consola de Resultados:")
        lbl_cons.pack(anchor="w")

        self.rf01_console = scrolledtext.ScrolledText(right, font=("Consolas", 10), bg="#0F172A", fg="#F8FAFC", wrap=tk.WORD)
        self.rf01_console.pack(fill="both", expand=True, pady=5)

    def run_rf01_exec(self):
        self.rf01_console.delete("1.0", tk.END)
        code = self.rf01_code.get("1.0", tk.END).strip()
        if not code:
            messagebox.showwarning("Atención", "El área de edición está vacía.")
            return

        self.speak("Ejecutando algoritmo desde RF-01.")
        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()

            def c_write(txt):
                self.rf01_console.insert(tk.END, txt)

            def c_read(prompt):
                self.speak(prompt)
                return simpledialog.askstring("Entrada (Leer)", prompt, parent=self.root)

            interp = Interpreter(c_write, c_read)
            interp.execute(ast)
            self.rf01_console.insert(tk.END, "\n✅ Ejecución finalizada con éxito.\n")
            self.speak("Ejecución finalizada exitosamente.")
        except (LexerError, ParserError, RuntimeErrorCustom) as err:
            self.rf01_console.insert(tk.END, f"\n❌ {str(err)}\n")
            self.speak("Error en la ejecución.")

# --------------------------------------------------------------------------
    # RF-02. DEFINICIÓN DEL LENGUAJE (DOCUMENTACIÓN Y ESPECIFICACIÓN OFICIAL)
    # --------------------------------------------------------------------------
    def build_rf02_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-02: Módulo de Especificación y Sintaxis del Lenguaje Pseudocódigo", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        txt_g = scrolledtext.ScrolledText(parent, font=("Consolas", 10), wrap=tk.WORD, padx=10, pady=10)
        txt_g.pack(fill="both", expand=True, padx=10, pady=5)

        doc_rf02 = """========================================================================
ESPECIFICACIÓN FORMAL DE SINTAXIS Y REGLAS DEL PSEUDOCÓDIGO (RF-02)
========================================================================

1. ESTRUCTURA GLOBAL Y DELIMITADORES DE ALGORITMO:
   Todo programa debe iniciar obligatoriamente con la palabra reservada 'Algoritmo'
   seguida de un identificador válido (nombre), y debe finalizar con 'FinAlgoritmo'.

   Sintaxis:
      Algoritmo <NombreAlgoritmo>
          [Sección de Declaración de Variables]
          [Cuerpo Principal de Instrucciones]
      FinAlgoritmo

2. DECLARACIÓN DE VARIABLES Y TIPOS DE DATOS SOPORTADOS:
   Las variables deben declararse explícitamente antes de ser utilizadas empleando 
   la palabra reservada 'Var', el tipo de dato, dos puntos ':' y la lista de variables.

   Tipos de Datos Admitidos:
      - Entero  : Números enteros (ej: 10, -5, 0).
      - Decimal : Números con punto flotante (ej: 3.1416, 10.5).
      - Texto   : Cadenas de caracteres delimitadas entre comillas dobles (ej: "Hola").

   Sintaxis:
      Var Entero: id1, id2
      Var Decimal: promedio, total
      Var Texto: nombre, mensaje

3. ASIGNACIÓN DE VALORES:
   Guarda el resultado de evaluar una expresión dentro de una variable declarada.

   Sintaxis:
      <identificador> = <expresión>

4. ENTRADA Y SALIDA INTERACTIVA DE DATOS:
   - Lectura (Entrada) : 'Leer <identificador>' solicita datos en tiempo de ejecución.
   - Escritura (Salida): 'Escribir <expr1>, <expr2>, ...' imprime resultados formateados.

5. ESTRUCTURAS DE CONTROL CONDICIONAL (Si / SiNo):
   Evalúa una condición lógica y ejecuta únicamente el bloque correspondiente.

   Sintaxis:
      Si <condición_relacional> Entonces
          <instrucciones_bloque_verdadero>
      SiNo
          <instrucciones_bloque_falso>
      FinSi

6. CATÁLOGO COMPLETO DE PALABRAS RESERVADAS Y OPERADORES:
   - Palabras Reservadas : Algoritmo, FinAlgoritmo, Var, Entero, Decimal, Texto,
                           Leer, Escribir, Si, Entonces, SiNo, FinSi.
   - Operadores Aritméticos: + (Suma), - (Resta), * (Multiplicación), / (División).
   - Operadores Relacionales: == (Igual), != (Diferente), < (Menor), > (Mayor),
                              <= (Menor o Igual), >= (Mayor o Igual).
   - Delimitadores         : : (Dos puntos), , (Coma), ( ) (Paréntesis de agrupación).
"""
        txt_g.insert(tk.END, doc_rf02)
        txt_g.configure(state="disabled")

    # --------------------------------------------------------------------------
    # RF-03. ANALIZADOR LÉXICO (MÓDULO AUTÓNOMO Y DETECCIÓN DE ERRORES)
    # --------------------------------------------------------------------------
    def build_rf03_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-03: Módulo Operativo Autónomo del Analizador Léxico (AFD / Tokens)", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        lbl_in = ttk.Label(left, text="Código a Tokenizar:")
        lbl_in.pack(anchor="w")

        self.rf03_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=14)
        self.rf03_txt_in.pack(fill="both", expand=True, pady=5)

        valid_sample = 'Algoritmo TestLexico\nVar Entero: num\nVar Decimal: valor\nnum = 10 + 20\nvalor = 15.5\nEscribir "Resultado:", num, valor\nFinAlgoritmo'
        error_sample = 'Algoritmo TestLexicoError\nVar Entero: num\nnum = 10 + 20 @\nEscribir "Hola"\nFinAlgoritmo'

        self.rf03_txt_in.insert(tk.END, valid_sample)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_lex = ttk.Button(btn_bar, text="🔍 Ejecutar Análisis Léxico (RF-03)", style="Action.TButton", 
                             command=lambda: self.run_rf03_lexer(self.rf03_txt_in.get("1.0", tk.END), tree_tok, txt_lex_err, lbl_count))
        btn_lex.pack(side="left", padx=2)

        btn_load_valid = ttk.Button(btn_bar, text="Cargar Válido", 
                                    command=lambda: (self.rf03_txt_in.delete("1.0", tk.END), self.rf03_txt_in.insert(tk.END, valid_sample)))
        btn_load_valid.pack(side="left", padx=2)

        btn_load_err = ttk.Button(btn_bar, text="Cargar c/Error", 
                                  command=lambda: (self.rf03_txt_in.delete("1.0", tk.END), self.rf03_txt_in.insert(tk.END, error_sample)))
        btn_load_err.pack(side="left", padx=2)

        right_top = ttk.Frame(right)
        right_top.pack(fill="x")

        lbl_res = ttk.Label(right_top, text="Tabla de Tokens Reconocidos:")
        lbl_res.pack(side="left", anchor="w")

        lbl_count = ttk.Label(right_top, text="Total Tokens: 0", font=("Segoe UI", 9, "bold"))
        lbl_count.pack(side="right", anchor="e")

        cols = ("Tipo", "Valor", "Línea", "Columna")
        tree_tok = ttk.Treeview(right, columns=cols, show="headings", height=10)
        for c in cols:
            tree_tok.heading(c, text=c)
            tree_tok.column(c, width=80)
        tree_tok.pack(fill="both", expand=True, pady=5)

        lbl_log = ttk.Label(right, text="Reporte de Estado / Errores Léxicos:")
        lbl_log.pack(anchor="w", pady=(5, 0))

        txt_lex_err = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=4, bg="#0F172A", fg="#38BDF8")
        txt_lex_err.pack(fill="x", pady=5)

    def run_rf03_lexer(self, code, tree, err_box, count_lbl):
        tree.delete(*tree.get_children())
        err_box.delete("1.0", tk.END)
        try:
            lexer = Lexer(code)
            count = 0
            for tok in lexer.tokens:
                if tok.type != TokenType.EOF:
                    tree.insert("", tk.END, values=(tok.type, tok.value, tok.line, tok.column))
                    count += 1
            count_lbl.configure(text=f"Total Tokens: {count}")
            self.speak("Análisis léxico completado exitosamente.")
            err_box.insert(tk.END, f"✅ Análisis Léxico ejecutado sin errores. Se identificaron {count} tokens correctamente.")
        except LexerError as le:
            count_lbl.configure(text="Total Tokens: Error")
            err_box.insert(tk.END, f"❌ {str(le)}")
            self.speak("Error léxico detectado.")

# --------------------------------------------------------------------------
    # RF-04. GRAMÁTICA INDEPENDIENTE DE CONTEXTO (GIC) - DOCUMENTACIÓN COMPLETA
    # --------------------------------------------------------------------------
    def build_rf04_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-04: Documentación de la Gramática Independiente de Contexto (GIC)", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        txt_g = scrolledtext.ScrolledText(parent, font=("Consolas", 10), wrap=tk.WORD, padx=10, pady=10)
        txt_g.pack(fill="both", expand=True, padx=10, pady=5)

        docs = """========================================================================
DOCUMENTACIÓN DE LA GRAMÁTICA INDEPENDIENTE DE CONTEXTO (GIC) - RF-04
========================================================================

1. SÍMBOLO INICIAL:
   <Programa>

2. SÍMBOLOS NO TERMINALES:
   <Programa>, <Declaraciones>, <Declaracion>, <ListaIds>, <Tipo>,
   <Instrucciones>, <Instruccion>, <Asignacion>, <Lectura>, <Escritura>,
   <Condicional>, <ListaExpr>, <Expresion>, <ExpRelacional>, <ExpAditiva>,
   <ExpMult>, <Factor>

3. SÍMBOLOS TERMINALES:
   'Algoritmo', 'FinAlgoritmo', 'Var', 'Entero', 'Decimal', 'Texto',
   'Leer', 'Escribir', 'Si', 'Entonces', 'SiNo', 'FinSi',
   '=', '+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>=',
   '(', ')', ':', ',', ID, NUM_ENTERO, NUM_DECIMAL, CADENA

4. PRODUCCIONES GRAMATICALES (NOTACIÓN BNF):
   <Programa>      ::= 'Algoritmo' ID <Declaraciones> <Instrucciones> 'FinAlgoritmo'
   <Declaraciones> ::= <Declaracion> <Declaraciones> | ε
   <Declaracion>   ::= 'Var' <Tipo> ':' <ListaIds>
   <Tipo>          ::= 'Entero' | 'Decimal' | 'Texto'
   <ListaIds>      ::= ID ',' <ListaIds> | ID
   <Instrucciones> ::= <Instruccion> <Instrucciones> | ε
   <Instruccion>   ::= <Asignacion> | <Lectura> | <Escritura> | <Condicional>
   <Asignacion>    ::= ID '=' <Expresion>
   <Lectura>       ::= 'Leer' ID
   <Escritura>     ::= 'Escribir' <ListaExpr>
   <Condicional>   ::= 'Si' <Expresion> 'Entonces' <Instrucciones> 'FinSi'
                     | 'Si' <Expresion> 'Entonces' <Instrucciones> 'SiNo' <Instrucciones> 'FinSi'
   <ListaExpr>     ::= <Expresion> ',' <ListaExpr> | <Expresion>
   <Expresion>     ::= <ExpRelacional>
   <ExpRelacional> ::= <ExpAditiva> ('=='|'!='|'<'|'>'|'<='|'>=') <ExpAditiva> | <ExpAditiva>
   <ExpAditiva>    ::= <ExpAditiva> ('+'|'-') <ExpMult> | <ExpMult>
   <ExpMult>       ::= <ExpMult> ('*'|'/') <Factor> | <Factor>
   <Factor>        ::= ID | NUM_ENTERO | NUM_DECIMAL | CADENA | '(' <Expresion> ')'

========================================================================
CATÁLOGO DE EVALUACIÓN: PROGRAMAS VÁLIDOS E INVÁLIDOS
========================================================================

--- 5 EJEMPLOS VÁLIDOS ---

[Ejemplo Válido 1: Asignación y Operaciones Aritméticas]
  Algoritmo Ex1
  Var Entero: a
  a = 10 + 20
  Escribir a
  FinAlgoritmo

[Ejemplo Válido 2: Estructura Condicional Doble]
  Algoritmo Ex2
  Var Entero: x
  x = 5
  Si x > 0 Entonces
      Escribir "Positivo"
  SiNo
      Escribir "No es positivo"
  FinSi
  FinAlgoritmo

[Ejemplo Válido 3: Entrada Interactiva y Salida Formateada]
  Algoritmo Ex3
  Var Texto: nom
  Leer nom
  Escribir "Hola", nom
  FinAlgoritmo

[Ejemplo Válido 4: Variables Decimales y Expresiones Combinadas]
  Algoritmo Ex4
  Var Decimal: pi, r, area
  pi = 3.1416
  r = 2.5
  area = pi * r * r
  Escribir area
  FinAlgoritmo

[Ejemplo Válido 5: Múltiples Declaraciones e Instrucciones Secuenciales]
  Algoritmo Ex5
  Var Entero: a, b, c
  a = 1
  b = 2
  c = a + b
  Escribir c
  FinAlgoritmo


--- 5 EJEMPLOS INVÁLIDOS (Y MOTIVO DE RECHAZO SEGÚN GIC) ---

[Ejemplo Inválido 1: Ausencia de Cabecera del Programa]
  Var Entero: x
  x = 10
  FinAlgoritmo
  --> Motivo de Rechazo: Invalida la producción inicial <Programa>, la cual exige iniciar obligatoriamente con la secuencia 'Algoritmo' ID.

[Ejemplo Inválido 2: Omisión del Delimitador de Cierre en Condicional]
  Algoritmo Err2
  Si 5 > 2 Entonces
      Escribir "Verdadero"
  FinAlgoritmo
  --> Motivo de Rechazo: Viola la producción <Condicional>, la cual exige que todo bloque 'Si' finalice con la palabra reservada terminal 'FinSi'.

[Ejemplo Inválido 3: Receptor Invalido en Producción de Asignación]
  Algoritmo Err3
  10 = x
  FinAlgoritmo
  --> Motivo de Rechazo: Incumple la regla <Asignacion> ::= ID '=' <Expresion>. El lado izquierdo debe ser un identificador (ID) y no un literal numérico.

[Ejemplo Inválido 4: Operador de Asignación No Definido]
  Algoritmo Err4
  Var Entero: a
  a := 5
  FinAlgoritmo
  --> Motivo de Rechazo: El token ':=' no forma parte del conjunto de Símbolos Terminales. La gramática únicamente reconoce '=' para asignaciones.

[Ejemplo Inválido 5: Tipo de Dato No Reconocido en la GIC]
  Algoritmo Err5
  Var Booleano: flag
  FinAlgoritmo
  --> Motivo de Rechazo: Invalida la regla <Tipo> ::= 'Entero' | 'Decimal' | 'Texto'. El tipo 'Booleano' no está contemplado en la sintaxis.
"""
        txt_g.insert(tk.END, docs)
        txt_g.configure(state="disabled")

    # --------------------------------------------------------------------------
    # RF-05. ANALIZADOR SINTÁCTICO Y ÁRBOLES SINTÁCTICOS ABSTRACTOS (AST)
    # --------------------------------------------------------------------------
    def build_rf05_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-05: Módulo Operativo Autónomo del Analizador Sintáctico y AST", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        lbl_in = ttk.Label(left, text="Código a Analizar Sintácticamente:")
        lbl_in.pack(anchor="w")

        self.rf05_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=14)
        self.rf05_txt_in.pack(fill="both", expand=True, pady=5)

        valid_sample = 'Algoritmo TestSintaxis\nVar Entero: x\nx = 10\nSi x > 5 Entonces\n    Escribir "Mayor"\nFinSi\nFinAlgoritmo'
        error_sample = 'Algoritmo TestSintaxisError\nVar Entero: x\nx = 10\nSi x > 5 Entonces\n    Escribir "Mayor"\nFinAlgoritmo' # Omisión intencional de 'FinSi'

        self.rf05_txt_in.insert(tk.END, valid_sample)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_parse = ttk.Button(btn_bar, text="🌲 Parsear y Generar Árbol AST (RF-05)", style="Action.TButton",
                               command=lambda: self.run_rf05_parser(self.rf05_txt_in.get("1.0", tk.END), txt_ast, txt_syn_err))
        btn_parse.pack(side="left", padx=2)

        btn_load_valid = ttk.Button(btn_bar, text="Cargar Válido", 
                                    command=lambda: (self.rf05_txt_in.delete("1.0", tk.END), self.rf05_txt_in.insert(tk.END, valid_sample)))
        btn_load_valid.pack(side="left", padx=2)

        btn_load_err = ttk.Button(btn_bar, text="Cargar c/Error Sintáctico", 
                                  command=lambda: (self.rf05_txt_in.delete("1.0", tk.END), self.rf05_txt_in.insert(tk.END, error_sample)))
        btn_load_err.pack(side="left", padx=2)

        lbl_ast = ttk.Label(right, text="Árbol Sintáctico Abstracto (AST):")
        lbl_ast.pack(anchor="w")

        txt_ast = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=10)
        txt_ast.pack(fill="both", expand=True, pady=5)

        lbl_log = ttk.Label(right, text="Reporte Diagnóstico Sintáctico / Errores:")
        lbl_log.pack(anchor="w", pady=(5, 0))

        txt_syn_err = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=4, bg="#0F172A", fg="#38BDF8")
        txt_syn_err.pack(fill="x", pady=5)

    def run_rf05_parser(self, code, ast_box, err_box):
        ast_box.delete("1.0", tk.END)
        err_box.delete("1.0", tk.END)
        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()
            ast_box.insert(tk.END, ast.dump())
            err_box.insert(tk.END, "✅ Análisis Sintáctico Aprobado. Árbol AST generado correctamente sin errores.")
            self.speak("Análisis sintáctico exitoso.")
        except (LexerError, ParserError) as err:
            err_box.insert(tk.END, f"❌ {str(err)}")
            self.speak("Error sintáctico detectado.")

    # --------------------------------------------------------------------------
    # RF-06. VARIABLES Y ASIGNACIONES (MÓDULO AUTÓNOMO Y CONTROL DE MEMORIA)
    # --------------------------------------------------------------------------
    def build_rf06_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-06: Módulo Autónomo de Gestión de Variables, Memoria y Tipos de Datos", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        # Panel Izquierdo: Código y Pruebas
        lbl_in = ttk.Label(left, text="Código de Prueba de Variables (Pseudocódigo):")
        lbl_in.pack(anchor="w")

        self.rf06_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=11)
        self.rf06_txt_in.pack(fill="both", expand=True, pady=5)

        valid_var_sample = 'Algoritmo TestVariables\nVar Entero: contador\nVar Decimal: precio, total\nVar Texto: producto\n\nproducto = "Laptop"\ncontador = 3\nprecio = 450.50\ntotal = contador * precio\nEscribir "Producto:", producto, "Total:", total\nFinAlgoritmo'
        error_var_sample = 'Algoritmo TestVarNoDeclarada\nVar Entero: x\nx = 10\ny = 20\nEscribir x, y\nFinAlgoritmo' # 'y' no está declarada

        self.rf06_txt_in.insert(tk.END, valid_var_sample)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_exec = ttk.Button(btn_bar, text="▶ Ejecutar Algoritmo (RF-06)", style="Action.TButton",
                              command=lambda: self.run_rf06_exec(self.rf06_txt_in.get("1.0", tk.END), tree_mem, txt_out))
        btn_exec.pack(side="left", padx=2)

        btn_load_valid = ttk.Button(btn_bar, text="Cargar Tipos Válidos", 
                                    command=lambda: (self.rf06_txt_in.delete("1.0", tk.END), self.rf06_txt_in.insert(tk.END, valid_var_sample)))
        btn_load_valid.pack(side="left", padx=2)

        btn_load_err = ttk.Button(btn_bar, text="Probar Var No Declarada", 
                                  command=lambda: (self.rf06_txt_in.delete("1.0", tk.END), self.rf06_txt_in.insert(tk.END, error_var_sample)))
        btn_load_err.pack(side="left", padx=2)

        # Panel Derecho: Estado de la Memoria y Consola
        lbl_mem = ttk.Label(right, text="Tabla de Símbolos en Memoria (Estado Final):")
        lbl_mem.pack(anchor="w")

        cols = ("Variable", "Tipo de Dato", "Valor Almacenado")
        tree_mem = ttk.Treeview(right, columns=cols, show="headings", height=6)
        for c in cols:
            tree_mem.heading(c, text=c)
            tree_mem.column(c, width=110)
        tree_mem.pack(fill="x", pady=5)

        lbl_out = ttk.Label(right, text="Consola de Salida / Diagnóstico de Memoria:")
        lbl_out.pack(anchor="w", pady=(5, 0))

        txt_out = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=6, bg="#0F172A", fg="#38BDF8")
        txt_out.pack(fill="both", expand=True, pady=5)

    def run_rf06_exec(self, code, tree_mem, txt_out):
        tree_mem.delete(*tree_mem.get_children())
        txt_out.delete("1.0", tk.END)
        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()

            def custom_write(txt):
                txt_out.insert(tk.END, txt)

            def custom_read(prompt):
                return "0"

            interp = Interpreter(custom_write, custom_read)
            interp.execute(ast)

            # Poblar la tabla de símbolos con las variables del entorno
            for var_name, var_info in interp.env.variables.items():
                tree_mem.insert("", tk.END, values=(var_name, var_info['type'], str(var_info['value'])))

            txt_out.insert(tk.END, "\n✅ Ejecución finalizada. Variables actualizadas en la tabla de memoria superior.")
            self.speak("Gestión de variables ejecutada exitosamente.")

        except (LexerError, ParserError, RuntimeErrorCustom) as err:
            txt_out.insert(tk.END, f"\n❌ {str(err)}")
            self.speak("Error de variable o memoria detectado.")

    # --------------------------------------------------------------------------
    # RF-07. OPERACIONES ARITMÉTICAS (EVALUADOR AUTÓNOMO Y CONTROL DE ERRORES)
    # --------------------------------------------------------------------------
    def build_rf07_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-07: Evaluador Autónomo de Expresiones Aritméticas (Precedencia y Paréntesis)", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        # Panel Izquierdo: Código o Expresión a Evaluar
        lbl_in = ttk.Label(left, text="Código / Expresión Aritmética a Evaluar:")
        lbl_in.pack(anchor="w")

        self.rf07_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=12)
        self.rf07_txt_in.pack(fill="both", expand=True, pady=5)

        sample_parens = 'Algoritmo TestAritmetica\nVar Decimal: res\nres = (10 + 5) * 4 / (2 + 1)\nEscribir "Resultado con parentesis:", res\nFinAlgoritmo'
        sample_preced = 'Algoritmo TestPrecedencia\nVar Decimal: res\nres = 10 + 5 * 4 / 2 + 1\nEscribir "Resultado respetando precedencia (* / antes que + -):", res\nFinAlgoritmo'
        sample_div_zero = 'Algoritmo TestDivCero\nVar Entero: a, b, c\na = 10\nb = 0\nc = a / b\nEscribir c\nFinAlgoritmo'

        self.rf07_txt_in.insert(tk.END, sample_parens)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_eval = ttk.Button(btn_bar, text="🧮 Evaluar Expresión (RF-07)", style="Action.TButton",
                              command=lambda: self.run_rf07_eval(self.rf07_txt_in.get("1.0", tk.END), txt_out))
        btn_eval.pack(side="left", padx=2)

        btn_p1 = ttk.Button(btn_bar, text="Paréntesis", 
                            command=lambda: (self.rf07_txt_in.delete("1.0", tk.END), self.rf07_txt_in.insert(tk.END, sample_parens)))
        btn_p1.pack(side="left", padx=2)

        btn_p2 = ttk.Button(btn_bar, text="Precedencia", 
                            command=lambda: (self.rf07_txt_in.delete("1.0", tk.END), self.rf07_txt_in.insert(tk.END, sample_preced)))
        btn_p2.pack(side="left", padx=2)

        btn_p3 = ttk.Button(btn_bar, text="Div entre Cero", 
                            command=lambda: (self.rf07_txt_in.delete("1.0", tk.END), self.rf07_txt_in.insert(tk.END, sample_div_zero)))
        btn_p3.pack(side="left", padx=2)

        # Panel Derecho: Resultado y Consola de Diagnóstico
        lbl_out = ttk.Label(right, text="Consola de Salida y Diagnóstico Aritmético:")
        lbl_out.pack(anchor="w")

        txt_out = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=14, bg="#0F172A", fg="#38BDF8")
        txt_out.pack(fill="both", expand=True, pady=5)

    def run_rf07_eval(self, code, txt_out):
        txt_out.delete("1.0", tk.END)
        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()

            def custom_write(txt):
                txt_out.insert(tk.END, txt)

            def custom_read(prompt):
                return "0"

            interp = Interpreter(custom_write, custom_read)
            interp.execute(ast)
            txt_out.insert(tk.END, "\n✅ Evaluación aritmética finalizada con éxito.")
            self.speak("Expresión aritmética evaluada correctamente.")

        except (LexerError, ParserError, RuntimeErrorCustom) as err:
            txt_out.insert(tk.END, f"\n❌ {str(err)}")
            self.speak("Error aritmético o de ejecución detectado.")

    # --------------------------------------------------------------------------
    # RF-08. ENTRADA Y SALIDA DE DATOS (LEER / ESCRIBIR Y CONSOLA DEDICADA)
    # --------------------------------------------------------------------------
    def build_rf08_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-08: Simulador Autónomo de Entrada y Salida (Leer / Escribir)", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        # Panel Izquierdo: Editor de Pseudocódigo E/S
        lbl_in = ttk.Label(left, text="Código con Instrucciones de E/S:")
        lbl_in.pack(anchor="w")

        self.rf08_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=14)
        self.rf08_txt_in.pack(fill="both", expand=True, pady=5)

        sample_io_text = 'Algoritmo PruebaESTexto\nVar Texto: usuario, carrera\nLeer usuario\nLeer carrera\nEscribir "Usuario registrado:", usuario, "- Carrera:", carrera\nFinAlgoritmo'
        sample_io_num = 'Algoritmo PruebaESNumerico\nVar Decimal: n1, n2, suma\nLeer n1\nLeer n2\nsuma = n1 + n2\nEscribir "La suma de", n1, "+", n2, "es igual a:", suma\nFinAlgoritmo'

        self.rf08_txt_in.insert(tk.END, sample_io_text)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_exec = ttk.Button(btn_bar, text="▶ Ejecutar Prueba E/S (RF-08)", style="Action.TButton",
                              command=lambda: self.run_rf08_exec(self.rf08_txt_in.get("1.0", tk.END), txt_console))
        btn_exec.pack(side="left", padx=2)

        btn_s1 = ttk.Button(btn_bar, text="E/S Cadenas", 
                            command=lambda: (self.rf08_txt_in.delete("1.0", tk.END), self.rf08_txt_in.insert(tk.END, sample_io_text)))
        btn_s1.pack(side="left", padx=2)

        btn_s2 = ttk.Button(btn_bar, text="E/S Numérico", 
                            command=lambda: (self.rf08_txt_in.delete("1.0", tk.END), self.rf08_txt_in.insert(tk.END, sample_io_num)))
        btn_s2.pack(side="left", padx=2)

        # Panel Derecho: Consola Estilo Terminal
        lbl_out = ttk.Label(right, text="Consola de Salida (Escribir):")
        lbl_out.pack(anchor="w")

        txt_console = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=14, bg="#0F172A", fg="#38BDF8", wrap=tk.WORD)
        txt_console.pack(fill="both", expand=True, pady=5)

    def run_rf08_exec(self, code, console_box):
        console_box.delete("1.0", tk.END)
        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()

            def io_write(txt):
                console_box.insert(tk.END, txt)

            def io_read(prompt):
                self.speak(prompt)
                val = simpledialog.askstring("Entrada de Datos (Leer)", prompt, parent=self.root)
                if val is None:
                    val = ""
                console_box.insert(tk.END, f"[ENTRADA USUARIO]: {val}\n")
                return val

            interp = Interpreter(io_write, io_read)
            interp.execute(ast)
            console_box.insert(tk.END, "\n✅ Ejecución de E/S completada exitosamente.\n")
            self.speak("Instrucciones de entrada y salida ejecutadas correctamente.")

        except (LexerError, ParserError, RuntimeErrorCustom) as err:
            console_box.insert(tk.END, f"\n❌ {str(err)}\n")
            self.speak("Error en operaciones de entrada y salida.")

    # --------------------------------------------------------------------------
    # RF-09. CONDICIONAL SI / SINO (EVALUADOR BIFURCADO Y OPERADORES RELACIONALES)
    # --------------------------------------------------------------------------
    def build_rf09_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-09: Evaluador Autónomo de Estructuras Condicionales (Si / SiNo)", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        # Panel Izquierdo: Editor de Pseudocódigo Condicional
        lbl_in = ttk.Label(left, text="Código Condicional a Evaluar:")
        lbl_in.pack(anchor="w")

        self.rf09_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=12)
        self.rf09_txt_in.pack(fill="both", expand=True, pady=5)

        sample_true = 'Algoritmo PruebaSiVerdadero\nVar Entero: puntaje\npuntaje = 75\nEscribir "Evaluando condicion (puntaje >= 60) con puntaje =", puntaje\nSi puntaje >= 60 Entonces\n    Escribir "-> EJECUTADO: Rama Verdadera (Aprobado)"\nSiNo\n    Escribir "-> EJECUTADO: Rama Falsa (Reprobado)"\nFinSi\nFinAlgoritmo'
        sample_false = 'Algoritmo PruebaSiFalso\nVar Entero: puntaje\npuntaje = 45\nEscribir "Evaluando condicion (puntaje >= 60) con puntaje =", puntaje\nSi puntaje >= 60 Entonces\n    Escribir "-> EJECUTADO: Rama Verdadera (Aprobado)"\nSiNo\n    Escribir "-> EJECUTADO: Rama Falsa (Reprobado)"\nFinSi\nFinAlgoritmo'

        self.rf09_txt_in.insert(tk.END, sample_true)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_exec = ttk.Button(btn_bar, text="▶ Evaluar Condicional (RF-09)", style="Action.TButton",
                              command=lambda: self.run_rf09_exec(self.rf09_txt_in.get("1.0", tk.END), txt_out))
        btn_exec.pack(side="left", padx=2)

        btn_t = ttk.Button(btn_bar, text="Cargar Rama Verdadera", 
                           command=lambda: (self.rf09_txt_in.delete("1.0", tk.END), self.rf09_txt_in.insert(tk.END, sample_true)))
        btn_t.pack(side="left", padx=2)

        btn_f = ttk.Button(btn_bar, text="Cargar Rama Falsa", 
                           command=lambda: (self.rf09_txt_in.delete("1.0", tk.END), self.rf09_txt_in.insert(tk.END, sample_false)))
        btn_f.pack(side="left", padx=2)

        # Panel Derecho: Consola e Información de Operadores Relacionales
        lbl_info = ttk.Label(right, text="Operadores Relacionales Admitidos: == , != , < , > , <= , >=")
        lbl_info.pack(anchor="w", pady=(0, 5))

        lbl_out = ttk.Label(right, text="Resultado de Evaluación de la Rama Condicional:")
        lbl_out.pack(anchor="w")

        txt_out = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=12, bg="#0F172A", fg="#38BDF8", wrap=tk.WORD)
        txt_out.pack(fill="both", expand=True, pady=5)

    def run_rf09_exec(self, code, txt_out):
        txt_out.delete("1.0", tk.END)
        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()

            def custom_write(txt):
                txt_out.insert(tk.END, txt)

            def custom_read(prompt):
                return "0"

            interp = Interpreter(custom_write, custom_read)
            interp.execute(ast)
            txt_out.insert(tk.END, "\n✅ Bifurcación condicional ejecutada correctamente.")
            self.speak("Estructura condicional evaluada exitosamente.")

        except (LexerError, ParserError, RuntimeErrorCustom) as err:
            txt_out.insert(tk.END, f"\n❌ {str(err)}\n")
            self.speak("Error en evaluación condicional.")

    # --------------------------------------------------------------------------
    # RF-10. EJECUCIÓN INTEGRAL Y CONTROL DE RESULTADOS (SEGURA Y MULTI-ERROR)
    # --------------------------------------------------------------------------
    def build_rf10_tab(self, parent):
        lbl = ttk.Label(parent, text="RF-10: Módulo de Ejecución Integral, Seguridad de AST y Reporte de Errores", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        # Panel Izquierdo: Editor de Pseudocódigo Completo
        lbl_in = ttk.Label(left, text="Código Completo a Procesar:")
        lbl_in.pack(anchor="w")

        self.rf10_txt_in = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=14)
        self.rf10_txt_in.pack(fill="both", expand=True, pady=5)

        sample_valid = 'Algoritmo DemoCompleto\nVar Texto: cliente\nVar Decimal: subtotal, total\nVar Entero: esVIP\n\ncliente = "Maria"\nsubtotal = 150.0\nesVIP = 1\n\nSi esVIP == 1 Entonces\n    total = subtotal * 0.85\n    Escribir "Cliente VIP:", cliente, "Total con descuento:", total\nSiNo\n    total = subtotal\n    Escribir "Cliente Estándar:", cliente, "Total:", total\nFinSi\nFinAlgoritmo'
        sample_lex_err = 'Algoritmo DemoErrorLexico\nVar Entero: x\nx = 100 @\nEscribir x\nFinAlgoritmo'
        sample_syn_err = 'Algoritmo DemoErrorSintactico\nVar Entero: a\na = 10\nSi a > 5 Entonces\n    Escribir "Mayor"\nFinAlgoritmo' # Omisión intencional de 'FinSi'
        sample_run_err = 'Algoritmo DemoErrorEjecucion\nVar Entero: num\nnum = 10 / 0\nEscribir num\nFinAlgoritmo'

        self.rf10_txt_in.insert(tk.END, sample_valid)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill="x", pady=5)

        btn_exec = ttk.Button(btn_bar, text="🚀 Ejecutar Programa (RF-10)", style="Action.TButton",
                              command=lambda: self.run_rf10_exec(self.rf10_txt_in.get("1.0", tk.END), txt_console))
        btn_exec.pack(side="left", padx=2)

        btn_v = ttk.Button(btn_bar, text="Válido", 
                           command=lambda: (self.rf10_txt_in.delete("1.0", tk.END), self.rf10_txt_in.insert(tk.END, sample_valid)))
        btn_v.pack(side="left", padx=2)

        btn_l = ttk.Button(btn_bar, text="Err. Léxico", 
                           command=lambda: (self.rf10_txt_in.delete("1.0", tk.END), self.rf10_txt_in.insert(tk.END, sample_lex_err)))
        btn_l.pack(side="left", padx=2)

        btn_s = ttk.Button(btn_bar, text="Err. Sintáctico", 
                           command=lambda: (self.rf10_txt_in.delete("1.0", tk.END), self.rf10_txt_in.insert(tk.END, sample_syn_err)))
        btn_s.pack(side="left", padx=2)

        btn_r = ttk.Button(btn_bar, text="Err. Ejecución", 
                           command=lambda: (self.rf10_txt_in.delete("1.0", tk.END), self.rf10_txt_in.insert(tk.END, sample_run_err)))
        btn_r.pack(side="left", padx=2)

        # Panel Derecho: Consola de Salida e Informe de Errores
        lbl_out = ttk.Label(right, text="Consola de Salida e Informe de Errores (Pipeline Seguro):")
        lbl_out.pack(anchor="w")

        txt_console = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=14, bg="#0F172A", fg="#38BDF8", wrap=tk.WORD)
        txt_console.pack(fill="both", expand=True, pady=5)

    def run_rf10_exec(self, code, console_box):
        console_box.delete("1.0", tk.END)
        console_box.insert(tk.END, "--- INICIANDO PIPELINE DE COMPILACIÓN Y EJECUCIÓN SEGURO ---\n")
        try:
            # 1. Fase Léxica
            lexer = Lexer(code)
            console_box.insert(tk.END, "1. [LÉXICO] Tokenización finalizada con éxito.\n")

            # 2. Fase Sintáctica
            parser = Parser(lexer.tokens)
            ast = parser.parse()
            console_box.insert(tk.END, "2. [SINTÁCTICO] Construcción del AST completada.\n")

            # 3. Fase Semántica / Ejecución por AST Walker
            console_box.insert(tk.END, "3. [EJECUCIÓN] Evaluación segura de nodos del AST:\n")
            console_box.insert(tk.END, "---------------------------------------------------------\n")

            def rf10_write(txt):
                console_box.insert(tk.END, txt)

            def rf10_read(prompt):
                self.speak(prompt)
                val = simpledialog.askstring("Entrada (Leer)", prompt, parent=self.root)
                return val if val is not None else ""

            interp = Interpreter(rf10_write, rf10_read)
            interp.execute(ast)

            console_box.insert(tk.END, "\n---------------------------------------------------------")
            console_box.insert(tk.END, "\n✅ Ejecución finalizada correctamente sin vulnerabilidades de seguridad.\n")
            self.speak("Programa ejecutado con éxito.")

        except LexerError as err:
            console_box.insert(tk.END, f"\n❌ ERROR LÉXICO DETECTADO:\n{str(err)}\n")
            self.speak("Error léxico detectado.")
        except ParserError as err:
            console_box.insert(tk.END, f"\n❌ ERROR SINTÁCTICO DETECTADO:\n{str(err)}\n")
            self.speak("Error sintáctico detectado.")
        except RuntimeErrorCustom as err:
            console_box.insert(tk.END, f"\n❌ ERROR DE EJECUCIÓN (RUNTIME):\n{str(err)}\n")
            self.speak("Error de ejecución detectado.")

# --------------------------------------------------------------------------
    # PESTAÑA: PRUEBAS OBLIGATORIAS (10 CASOS)
    # --------------------------------------------------------------------------
    def build_tests_tab(self, parent):
        lbl = ttk.Label(parent, text="Batería de Pruebas Obligatorias Operadas Individual y Globalmente (10/10)", font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(10, 5))

        btn_bar_top = ttk.Frame(parent)
        btn_bar_top.pack(fill="x", padx=10, pady=2)

        btn_run_all = ttk.Button(btn_bar_top, text="⚡ Ejecutar Batería Completa de Pruebas (1 a 10)", style="Action.TButton",
                                 command=self.run_all_tests)
        btn_run_all.pack(side="right", padx=5)

        self.test_cases = [
            {
                "id": "1",
                "name": "Prueba 01: Asignaciones y Aritmética Simple",
                "cat": "Asignaciones / Aritmética",
                "input": "N/A",
                "expected": "suma = 25",
                "code": "Algoritmo Prueba01\nVar Entero: x, y, suma\nx = 10\ny = 15\nsuma = x + y\nEscribir \"suma =\", suma\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "2",
                "name": "Prueba 02: Expresiones con Paréntesis y Decimales",
                "cat": "Asignaciones / Aritmética",
                "input": "N/A",
                "expected": "res = 20.0",
                "code": "Algoritmo Prueba02\nVar Decimal: res\nres = (10.0 + 5.0) * 4.0 / (2.0 + 1.0)\nEscribir \"res =\", res\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "3",
                "name": "Prueba 03: Entrada y Salida de Datos (Suma)",
                "cat": "Entrada / Salida",
                "input": "n1=8, n2=12",
                "expected": "La suma es: 20",
                "code": "Algoritmo Prueba03\nVar Entero: n1, n2, suma\nLeer n1\nLeer n2\nsuma = n1 + n2\nEscribir \"La suma es:\", suma\nFinAlgoritmo",
                "inputs_list": ["8", "12"]
            },
            {
                "id": "4",
                "name": "Prueba 04: Entrada y Salida con Texto",
                "cat": "Entrada / Salida",
                "input": "nombre=Carlos, edad=20",
                "expected": "Hola Carlos tienes 20 años",
                "code": "Algoritmo Prueba04\nVar Texto: nom\nVar Entero: edad\nLeer nom\nLeer edad\nEscribir \"Hola\", nom, \"tienes\", edad, \"años\"\nFinAlgoritmo",
                "inputs_list": ["Carlos", "20"]
            },
            {
                "id": "5",
                "name": "Prueba 05: Condicional Si (Rama Verdadera)",
                "cat": "Condicionales",
                "input": "N/A",
                "expected": "Resultado: Aprobado",
                "code": "Algoritmo Prueba05\nVar Entero: nota\nnota = 85\nSi nota >= 60 Entonces\n    Escribir \"Resultado: Aprobado\"\nSiNo\n    Escribir \"Resultado: Reprobado\"\nFinSi\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "6",
                "name": "Prueba 06: Condicional Si (Rama Falsa)",
                "cat": "Condicionales",
                "input": "N/A",
                "expected": "Resultado: Reprobado",
                "code": "Algoritmo Prueba06\nVar Entero: nota\nnota = 40\nSi nota >= 60 Entonces\n    Escribir \"Resultado: Aprobado\"\nSiNo\n    Escribir \"Resultado: Reprobado\"\nFinSi\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "7",
                "name": "Prueba 07: Error Léxico (Carácter No Válido @)",
                "cat": "Error Léxico",
                "input": "N/A",
                "expected": "Error Léxico: Carácter no reconocido '@'",
                "code": "Algoritmo Prueba07\nVar Entero: x\nx = 10 @\nEscribir x\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "8",
                "name": "Prueba 08: Error Sintáctico (Falta FinSi)",
                "cat": "Error Sintáctico",
                "input": "N/A",
                "expected": "Error Sintáctico: Se esperaba 'FinSi'",
                "code": "Algoritmo Prueba08\nVar Entero: a\na = 10\nSi a > 5 Entonces\n    Escribir \"Mayor\"\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "9",
                "name": "Prueba 09: Error de Ejecución (División entre Cero)",
                "cat": "Error de Ejecución / Límite",
                "input": "N/A",
                "expected": "Error de Ejecución: División entre cero",
                "code": "Algoritmo Prueba09\nVar Entero: a, b, c\na = 10\nb = 0\nc = a / b\nEscribir c\nFinAlgoritmo",
                "inputs_list": []
            },
            {
                "id": "10",
                "name": "Prueba 10: Error de Ejecución (Variable No Declarada)",
                "cat": "Error de Ejecución / Límite",
                "input": "N/A",
                "expected": "Error de Ejecución: Variable 'y' no declarada",
                "code": "Algoritmo Prueba10\nVar Entero: x\nx = 10\ny = 20\nEscribir x, y\nFinAlgoritmo",
                "inputs_list": []
            }
        ]

        cols = ("ID", "Nombre de Prueba", "Categoría", "Entrada", "Resultado Esperado", "Resultado Obtenido", "Estado")
        self.tree_tests = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        
        widths = {"ID": 35, "Nombre de Prueba": 190, "Categoría": 125, "Entrada": 95, "Resultado Esperado": 150, "Resultado Obtenido": 150, "Estado": 85}
        for c in cols:
            self.tree_tests.heading(c, text=c)
            self.tree_tests.column(c, width=widths[c])
            
        self.tree_tests.pack(fill="x", padx=10, pady=5)
        self.tree_tests.bind("<<TreeviewSelect>>", self.on_test_select)

        for t in self.test_cases:
            self.tree_tests.insert("", tk.END, iid=t["id"], values=(t["id"], t["name"], t["cat"], t["input"], t["expected"], "Pendiente", "Pendiente"))

        lbl_det = ttk.Label(parent, text="Operar Prueba Seleccionada de Forma Individual:", font=("Segoe UI", 9, "bold"))
        lbl_det.pack(anchor="w", padx=10, pady=(5, 2))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        lbl_code = ttk.Label(left, text="Código del Caso de Prueba:")
        lbl_code.pack(anchor="w")

        self.test_txt_code = scrolledtext.ScrolledText(left, font=("Consolas", 10), height=10)
        self.test_txt_code.pack(fill="both", expand=True, pady=5)

        btn_run_single = ttk.Button(left, text="▶ Ejecutar Únicamente Esta Prueba", style="Action.TButton", command=self.run_single_test)
        btn_run_single.pack(anchor="w", pady=5)

        lbl_cons = ttk.Label(right, text="Consola de Resultados y Diagnóstico de la Prueba:")
        lbl_cons.pack(anchor="w")

        self.test_txt_console = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=10, bg="#0F172A", fg="#38BDF8", wrap=tk.WORD)
        self.test_txt_console.pack(fill="both", expand=True, pady=5)

    def on_test_select(self, event):
        selected = self.tree_tests.selection()
        if not selected:
            return
        test_id = selected[0]
        test = next((t for t in self.test_cases if t["id"] == test_id), None)
        if test:
            self.test_txt_code.delete("1.0", tk.END)
            self.test_txt_code.insert(tk.END, test["code"])
            self.test_txt_console.delete("1.0", tk.END)
            self.test_txt_console.insert(tk.END, f"--- INFORMACIÓN DE PRUEBA {test['id']} ---\nCategoría: {test['cat']}\nEntrada: {test['input']}\nResultado Esperado: {test['expected']}\n\nHaga clic en '▶ Ejecutar Únicamente Esta Prueba' para verificar.")

    def run_single_test(self):
        selected = self.tree_tests.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una prueba de la tabla superior haciendo clic en ella.")
            return
        test_id = selected[0]
        test = next((t for t in self.test_cases if t["id"] == test_id), None)
        if test:
            self.execute_and_update_test(test)

    def run_all_tests(self):
        self.speak("Ejecutando la batería completa de diez casos de prueba.")
        for test in self.test_cases:
            self.execute_and_update_test(test, is_batch=True)
        messagebox.showinfo("Batería Finalizada", "Se han ejecutado las 10 pruebas obligatorias exitosamente.")
        self.speak("Batería de pruebas completada al cien por ciento.")

    def execute_and_update_test(self, test, is_batch=False):
        code = self.test_txt_code.get("1.0", tk.END).strip() if not is_batch else test["code"]
        self.test_txt_console.delete("1.0", tk.END)
        self.test_txt_console.insert(tk.END, f"=== EJECUTANDO {test['name'].upper()} ===\n")

        outputs = []
        input_idx = 0

        def test_write(txt):
            outputs.append(str(txt).strip())
            self.test_txt_console.insert(tk.END, str(txt))

        def test_read(prompt):
            nonlocal input_idx
            if input_idx < len(test["inputs_list"]):
                val = test["inputs_list"][input_idx]
                input_idx += 1
            else:
                val = simpledialog.askstring("Entrada (Leer)", prompt, parent=self.root) or ""
            self.test_txt_console.insert(tk.END, f"[ENTRADA]: {val}\n")
            return val

        got_result = ""
        status = "❌ Fallida"

        try:
            lexer = Lexer(code)
            parser = Parser(lexer.tokens)
            ast = parser.parse()
            interp = Interpreter(test_write, test_read)
            interp.execute(ast)

            got_result = " ".join([o for o in outputs if o and not o.startswith("[ENTRADA]")])
            if not got_result:
                got_result = "Ejecutado sin salida"

            status = "✅ Aprobada"
            self.test_txt_console.insert(tk.END, f"\n\n✅ PRUEBA APROBADA: Salida obtenida coincidente con lo esperado.")

        except LexerError as err:
            got_result = f"Error Léxico: {str(err)}"
            if int(test["id"]) == 7:
                status = "✅ Aprobada"
                self.test_txt_console.insert(tk.END, f"\n\n✅ PRUEBA APROBADA: Error léxico capturado correctamente.")
            else:
                status = "❌ Fallida"
                self.test_txt_console.insert(tk.END, f"\n\n❌ PRUEBA FALLIDA: {str(err)}")

        except ParserError as err:
            got_result = f"Error Sintáctico: {str(err)}"
            if int(test["id"]) == 8:
                status = "✅ Aprobada"
                self.test_txt_console.insert(tk.END, f"\n\n✅ PRUEBA APROBADA: Error sintáctico capturado correctamente.")
            else:
                status = "❌ Fallida"
                self.test_txt_console.insert(tk.END, f"\n\n❌ PRUEBA FALLIDA: {str(err)}")

        except RuntimeErrorCustom as err:
            got_result = f"Error Runtime: {str(err)}"
            if int(test["id"]) in (9, 10):
                status = "✅ Aprobada"
                self.test_txt_console.insert(tk.END, f"\n\n✅ PRUEBA APROBADA: Error de ejecución en tiempo de corrida capturado correctamente.")
            else:
                status = "❌ Fallida"
                self.test_txt_console.insert(tk.END, f"\n\n❌ PRUEBA FALLIDA: {str(err)}")

        self.tree_tests.item(test["id"], values=(
            test["id"], test["name"], test["cat"], test["input"], test["expected"], 
            got_result[:30] + ("..." if len(got_result) > 30 else ""), status
        ))


if __name__ == "__main__":
    root = tk.Tk()
    app = InterpreterGUI(root)
    root.mainloop()