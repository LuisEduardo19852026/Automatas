# 🚀 Intérprete Educativo de Pseudocódigo en Español

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![GUI Framework](https://img.shields.io/badge/GUI-Tkinter%20%2F%20ttk-00599C)
![TTS Engine](https://img.shields.io/badge/TTS-pyttsx3-green)
![Course](https://img.shields.io/badge/Curso-Aut%C3%B3matas%20y%20Lenguajes%20Formales-orange)
![Tests](https://img.shields.io/badge/Bater%C3%ADa%20de%20Pruebas-100%25%20Aprobada-brightgreen)

## 📋 Tabla de Contenidos
- [Descripción General](#-descripción-general)
- [Información Académica y Créditos](#-información-académica-y-créditos)
- [Fundamentos Teóricos de Autómatas y Compiladores](#-fundamentos-teóricos-de-autómatas-y-compiladores)
- [Arquitectura del Sistema y Pipeline](#-arquitectura-del-sistema-y-pipeline)
- [Requerimientos Funcionales (RF-01 a RF-10)](#-requerimientos-funcionales-rf-01-a-rf-10)
- [Tecnologías y Herramientas Utilizadas](#-tecnologías-y-herramientas-utilizadas)
- [Instrucciones de Instalación e Inicio](#-instrucciones-de-instalación-e-inicio)
- [Especificación Sintáctica del Lenguaje (GIC / BNF)](#-especificación-sintáctica-del-lenguaje-gic--bnf)
- [Matriz de la Batería de Pruebas Obligatorias (1 a 10)](#-matriz-de-la-batería-de-pruebas-obligatorias-1-a-10)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Licencia](#-licencia)

---

## 📖 Descripción General

El **Intérprete Educativo de Pseudocódigo** es un entorno de desarrollo interactivo de escritorio diseñado para facilitar el aprendizaje de la algoritmia básica en estudiantes de primer ingreso de la carrera de Ingeniería en Sistemas de Información.

El sistema permite escribir, analizar, depurar y ejecutar programas escritos en un pseudocódigo estructurado en español. A diferencia de un evaluador directo de cadenas o código genérico, este software aplica rigurosamente las fases teóricas de la disciplina de **Autómatas y Lenguajes Formales**: análisis léxico mediante Autómatas Finitos Deterministas (AFD), análisis sintáctico mediante un Parser Descendente Recursivo basado en una Gramática Independiente de Contexto (GIC) especificada en BNF, generación de un Árbol de Sintaxis Abstracta (AST) y un motor de evaluación en tiempo de ejecución con entorno de memoria dinámica.

### Objetivos Clave
1. **Didáctico:** Proporcionar mensajes diagnósticos precisos indicando coordenadas exactas de línea y columna ante errores léxicos, sintácticos y de tiempo de ejecución.
2. **Seguro:** Evaluar las instrucciones mediante el recorrido de nodos jerárquicos del AST (*AST Walker*), previniendo vulnerabilidades y la ejecución arbitraria de comandos del sistema operativo.
3. **Accesible:** Integrar asistente con respuesta por voz mediante síntesis de voz (Text-To-Speech) para acompañar la interacción en tiempo real.

---

## 🎓 Información Académica y Créditos

* **Institución:** Universidad Mariano Gálvez de Guatemala
* **Sede:** Regional de Retalhuleu
* **Facultad:** Ingeniería en Sistemas y Ciencias de la Computación
* **Curso:** Autómatas y Lenguajes Formales
* **Cátedra:** Ing. Guillermo Alexander Pisqui Fuentes
* **Lugar y Fecha:** Ciudad de Retalhuleu, Guatemala, 31 de octubre de 2026

### 👨‍💻 Equipo de Desarrollo
| Nombre Completo | Carné | Rol en el Proyecto |
| :--- | :---: | :--- |
| **Berlyn Marilú Ordoñez Rodas** | `2890-24-19614` | Diseño de Interfaz GUI y Módulo de Pruebas |
| **Edgar Oswaldo Quiche Vicente** | `2890-16-17204` | Especificación GIC / BNF y Analizador Sintáctico |
| **Leidy Vaneli Gutierrez Pérez** | `2890-24-24136` | Analizador Léxico (Lexer) y Tabla de Tokens |
| **Luis Eduardo Flores García** | `2890-21-12987` | Entorno de Ejecución (AST / Runtime / TTS) |

---

## 🧠 Fundamentos Teóricos de Autómatas y Compiladores

El proyecto implementa la teoría formal de lenguajes dividida en tres componentes centrales:

1. **Analizador Léxico (Lexer / Scanner):**
   - Transforma el flujo continuo de caracteres en una secuencia de tokens clasificados.
   - Aplica expresiones regulares y un Autómata Finito Determinista (AFD) para reconocer palabras reservadas, números enteros y decimales, cadenas de texto, operadores y delimitadores.
   - Registra metadatos de ubicación ($Línea, Columna$) para cada lexema encontrado.

2. **Analizador Sintáctico (Parser):**
   - Valida que la secuencia de tokens cumpla con la regla de producción gramatical.
   - Implementa la técnica de **Análisis Descendente Recursivo** derivada de una **Gramática Independiente de Contexto (GIC)** no ambigua.
   - Construye la estructura arbórea **Árbol de Sintaxis Abstracta (AST)**.

3. **Intérprete y Entorno de Memoria (Runtime / Environment):**
   - Realiza un recorrido en orden jerárquico (*Tree Walker*) sobre los nodos del AST.
   - Maneja la **Tabla de Símbolos** en memoria para asignación, verificación de tipos primitivos (`Entero`, `Decimal`, `Texto`) e interrupción en caso de variables no declaradas o excepciones aritméticas (ej. división entre cero).

---

## 🏗️ Arquitectura del Sistema y Pipeline

```
  +-----------------------+
  |  Código Pseudocódigo   |  (RF-01 / RF-02)
  +-----------+-----------+
              |
              v
  +-----------------------+
  |    Analizador Léxico   |  (RF-03: AFD / RegEx)
  |       (Lexer)         |  --> Produce lista de Tokens
  +-----------+-----------+
              |
              v
  +-----------------------+
  |  Analizador Sintáctico|  (RF-04 / RF-05: BNF)
  |       (Parser)        |  --> Genera el Árbol AST
  +-----------+-----------+
              |
              v
  +-----------------------+
  | Evaluador Semántico / |  (RF-06 a RF-10: Memoria y Pipeline)
  |   AST Walker Runtime  |  --> Ejecución y Consola
  +-----------------------+
```

---

## ⚙️ Requerimientos Funcionales (RF-01 a RF-10)

| ID | Requerimiento | Descripción Técnica |
| :---: | :--- | :--- |
| **RF-01** | **Editor de Pseudocódigo** | Área de edición con capacidad de corrección continua, controles de ejecución directa y consola integrada de resultados. |
| **RF-02** | **Definición del Lenguaje** | Definición formal de la sintaxis del pseudocódigo en español, delimitadores `Algoritmo` / `FinAlgoritmo` y palabras clave. |
| **RF-03** | **Analizador Léxico** | Clasificación de lexemas en un conjunto finito de tokens con detección y bloqueo ante caracteres ilegales. |
| **RF-04** | **Gramática (GIC)** | Formulación formal en Notación BNF, catálogo de 5 programas válidos y 5 programas inválidos documentados. |
| **RF-05** | **Analizador Sintáctico** | Verificación gramatical, construcción jerárquica del AST y diagnóstico descriptivo indicando línea y columna ante errores. |
| **RF-06** | **Variables y Asignación** | Gestión dinámica de la Tabla de Símbolos para tipos `Entero`, `Decimal` y `Texto`. Control de variables no declaradas. |
| **RF-07** | **Operaciones Aritméticas** | Evaluación con precedencia de operadores ($*, /$ sobre $+, -$), soporte de paréntesis agrupadores y captura de división por cero. |
| **RF-08** | **Entrada y Salida (E/S)** | Simulador interactivo con cuadros emergentes para `Leer` y consola formateada para la instrucción `Escribir`. |
| **RF-09** | **Condicional Si / SiNo** | Evaluación de operadores relacionales (`==`, `!=`, `<`, `>`, `<=`, `>=`) con bifurcación de control determinista. |
| **RF-10** | **Ejecución y Resultados** | Pipeline de compilación seguro en 3 fases sin evaluación arbitraria de código externo ni llamadas de sistema inseguras. |

---

## 🛠️ Tecnologías y Herramientas Utilizadas

* **Lenguaje de Programación:** Python 3.10+
* **Interfaz Gráfica de Usuario (GUI):** `tkinter` y `tkinter.ttk`
* **Widgets Avanzados de IU:** `tkinter.scrolledtext`, `tkinter.simpledialog`, `tkinter.messagebox`
* **Síntesis de Voz (TTS):** `pyttsx3` (Asistente de voz en segundo plano)
* **Concurrencia / Asincronía:** `threading` (Mapeo asíncrono de audio para evitar congelamiento de la GUI)
* **Procesamiento de Cadenas y RegEx:** Módulo nativo `re`
* **Notación Sintáctica:** BNF (Backus-Naur Form)
* **Control de Versiones:** Git y GitHub

---

## 💻 Instrucciones de Instalación e Inicio

Siga estos pasos para clonar, configurar y ejecutar la aplicación en su entorno local:

### 1. Requisitos Previos
Asegúrese de tener instalado Python en su versión 3.10 o superior.
```bash
python --version
```

### 2. Clonar el Repositorio
```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO
```

### 3. Crear y Activar un Entorno Virtual (Recomendado)
* **En Linux/macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
* **En Windows (PowerShell / CMD):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```

### 4. Instalar Dependencias
Instale la librería requerida para la voz sintética (`pyttsx3`):
```bash
pip install pyttsx3
```

> **Nota para usuarios de Linux (Ubuntu/Debian):** Si experimenta advertencias relacionadas con `espeak` o `tkinter`, ejecute:
> ```bash
> sudo apt-get install python3-tk espeak ffmpeg
> ```

### 5. Ejecutar la Aplicación
Inicie el programa ejecutando el archivo principal:
```bash
python app1_2.py
```

---

## 📜 Especificación Sintáctica del Lenguaje (GIC / BNF)

La estructura sintáctica del pseudocódigo se rige bajo las siguientes reglas de producción gramatical:

```bnf
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
```

---

## 🧪 Matriz de la Batería de Pruebas Obligatorias (1 a 10)

La aplicación incluye una pestaña interactiva (`🧪 Pruebas (1-10)`) que permite ejecutar de forma automatizada o individual la suite completa de 10 casos de prueba normativos:

| # | Nombre de la Prueba | Categoría | Entrada | Resultado Esperado | Estado |
| :-: | :--- | :--- | :--- | :--- | :-: |
| **01** | Asignaciones y Aritmética Simple | Asignación / Aritmética | $a=15, b=5$ | `El resultado es: 25` | **APROBADA** |
| **02** | Expresiones con Paréntesis y Decimales | Asignación / Aritmética | $x=10.5, y=4.5$ | `El valor final es: 5.0` | **APROBADA** |
| **03** | Entrada y Salida de Datos (Suma) | Entrada / Salida | $n_1=8, n_2=12$ | `La suma es: 20` | **APROBADA** |
| **04** | Entrada y Salida con Texto | Entrada / Salida | $nombre="Carlos", edad=20$ | `Hola Carlos tienes 20 años.` | **APROBADA** |
| **05** | Condicional Si (Rama Verdadera) | Condicionales | $nota=85$ | `Resultado: Aprobado` | **APROBADA** |
| **06** | Condicional Si (Rama Falsa) | Condicionales | $edad=15$ | `Es menor de edad` | **APROBADA** |
| **07** | Error Léxico (Carácter No Válido) | Error Léxico | Carácter `@` | `Error Léxico [Línea 3, Columna 14]...` | **APROBADA** |
| **08** | Error Sintáctico (Falta FinSi) | Error Sintáctico | Omisión `FinSi` | `Error Sintáctico [Línea 6, Columna 1]...` | **APROBADA** |
| **09** | Error de Ejecución (División entre Cero) | Runtime / Límite | Operación $10 / 0$ | `Error de Ejecución [Línea 5]: División entre cero...` | **APROBADA** |
| **10** | Error de Ejecución (Variable No Declarada) | Runtime / Límite | Uso de variable `y` | `Error de Ejecución [Línea 4]: Variable 'y' no declarada.` | **APROBADA** |

---

## 📁 Estructura del Proyecto

```
.
├── app1_2.py                                  # Código fuente principal de la aplicación
├── README.md                                  # Documentación técnica completa del repositorio
└── Proyecto Final de Automatas y Lenguajes Formales_2.pdf  # Informe final académico consolidado
```

---

## ⚖️ Licencia

Este proyecto ha sido desarrollado exclusivamente con fines académicos educativos para la **Universidad Mariano Gálvez de Guatemala (UMG) - Sede Retalhuleu**. Queda autorizada la revisión, prueba y uso con fines de evaluación educativa.