# Secuencia de Poda Alfa-Beta para la Memoria (Apartado 2.3)

Este archivo contiene el texto y la secuencia de intervalos $[\alpha, \beta]$ listos para copiar y pegar directamente en la memoria de la práctica (apartados *i*, *ii*, *iii* y *iv* de la página 10 del PDF sobre `SimpleGameTree`).

---

## 📋 Opción A: Texto completo redactado (Estilo estudiante, listo para pegar)

> ### 2.3. Comprobación teórica y experimental sobre el árbol de juego (SimpleGameTree)
> 
> Para comprobar que la poda está bien implementada y responder a los 4 apartados pedidos en el guion, primero resolvimos a mano el árbol de prueba propuesto por los profesores (con nodos de la A a la P) y luego lo ejecutamos en `demo_simple_game_tree.py` con `verbose=3` para contrastar los resultados:
> 
> 1. **Minimax puro**: Tras evaluar las tres ramas principales de la raíz, obtenemos los valores de $B = 3$, $C = 2$ y $D = 5$. Como la raíz $A$ busca maximizar, selecciona el valor óptimo **5** realizando la jugada **AD**. La salida por consola del primer turno confirma exactamente estos valores.
> 
> 2. **Poda Alfa-Beta**: Al activar la poda, la exploración genera la siguiente secuencia de intervalos $[\alpha, \beta]$ en cada nodo visitado:
>    
>    `A: [-inf, inf]` → `B: [-inf, inf]` → `B: [-inf, 4]` → `A: [3, inf]` → `C: [3, inf]` → `G: [3, inf]` → `G: [3, inf]` → `A: [3, inf]` → `D: [3, inf]` → `D: [3, 5]` → `J: [3, 5]` → `J: [4, 5]` → `J: [4, 5]`
> 
>    *(O desglosado por ramas para mayor claridad en el texto:)*
>    * **Rama B:** `A: [-inf, inf]` → `B: [-inf, inf]` → `B: [-inf, 4]` → `A: [3, inf]`
>    * **Rama C:** `C: [3, inf]` → `G: [3, inf]` → `G: [3, inf]` *(poda de H)* → `A: [3, inf]`
>    * **Rama D:** `D: [3, inf]` → `D: [3, 5]` → `J: [3, 5]` → `J: [4, 5]` → `J: [4, 5]` *(poda de P)*
> 
>    *(Si usas LaTeX, en varias líneas para no salirte del margen de la hoja:)*
>    ```latex
>    \begin{align*}
>    \text{A: } [-\infty, +\infty] &\rightarrow \text{B: } [-\infty, +\infty] \rightarrow \text{B: } [-\infty, 4] \rightarrow \text{A: } [3, +\infty] \\
>    &\rightarrow \text{C: } [3, +\infty] \rightarrow \text{G: } [3, +\infty] \rightarrow \text{G: } [3, +\infty] \rightarrow \text{A: } [3, +\infty] \\
>    &\rightarrow \text{D: } [3, +\infty] \rightarrow \text{D: } [3, 5] \rightarrow \text{J: } [3, 5] \rightarrow \text{J: } [4, 5] \rightarrow \text{J: } [4, 5]
>    \end{align*}
>    ```
> 
> 3. **Podas producidas**: Esta secuencia refleja con total fidelidad las dos podas que calculamos manualmente:
>    * **Poda Alfa en el nodo C**: Al evaluar el hijo $G$ se obtiene un valor de 2. Como estamos en un nodo MIN y $v = 2 \le \alpha = 3$, se corta la exploración de esa rama y **se descarta evaluar la hoja H (5)**.
>    * **Poda Beta en el subárbol J**: Tras evaluar la hoja $I$ (5), el nodo $D$ fija $\beta = 5$. Al entrar en $J$ (MAX), se evalúan $M$ (4), $N$ (2) y $O$ (6). Como $v = 6 \ge \beta = 5$, se produce el corte y **se descarta evaluar la hoja P (1)**.
> 
> 4. **Resultado final y jugadas**: El valor devuelto en la raíz sigue siendo **5** (demostrando que la poda no altera la decisión óptima). La partida completa se resuelve con el movimiento **AD** por parte del Jugador 1 (MAX), seguido de la respuesta **DI** por parte del Jugador 2 (MIN).

---

## 📌 Opción B: Respuestas directas a los apartados (i, ii, iii, iv)

Si el profesor pide responder de forma numerada a cada apartado del guion:

* **(i) Valor minimax en la raíz:**  
  El valor devuelto en la raíz $A$ es **5**. La mejor jugada para el Jugador 1 es **AD**.
* **(ii) Secuencia de intervalos $[\alpha, \beta]$:**  
  `A: [-inf, inf]` $\rightarrow$ `B: [-inf, inf]` $\rightarrow$ `B: [-inf, 4]` $\rightarrow$ `A: [3, inf]` $\rightarrow$ `C: [3, inf]` $\rightarrow$ `G: [3, inf]` $\rightarrow$ `G: [3, inf]` $\rightarrow$ `A: [3, inf]` $\rightarrow$ `D: [3, inf]` $\rightarrow$ `D: [3, 5]` $\rightarrow$ `J: [3, 5]` $\rightarrow$ `J: [4, 5]` $\rightarrow$ `J: [4, 5]`
* **(iii) Ramas / hojas podadas:**  
  Se podan 2 ramas:
  1. La **hoja H (5)** en el nodo $C$ por poda Alfa ($v = 2 \le \alpha = 3$).
  2. La **hoja P (1)** en el nodo $J$ por poda Beta ($v = 6 \ge \beta = 5$).
* **(iv) Secuencia de movimientos hasta el final de la partida:**  
  1. Jugador 1 mueve **AD** (nodo $D$, valor 5).  
  2. Jugador 2 mueve **DI** (nodo $I$, estado terminal, puntuación final: 5 para el Jugador 1 y 0 para el Jugador 2).

---

## 📊 Opción C: Tabla paso a paso (ideal para Word o LaTeX)

| Paso | Nodo visitado | Tipo | Intervalo $[\alpha, \beta]$ | Valor devuelto | Evento / Poda |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | **A** | MAX | $[-\infty, +\infty]$ | — | Raíz antes de explorar la rama $B$ |
| **2** | **B** | MIN | $[-\infty, +\infty]$ | — | Entrada a $B$ antes de evaluar la hoja $E$ (4) |
| **3** | **B** | MIN | $[-\infty, 4]$ | 3 | $B$ actualiza $\beta=4$ antes de evaluar $F$ (3). Devuelve 3 |
| **4** | **A** | MAX | $[3, +\infty]$ | — | $A$ actualiza $\alpha=3$ antes de explorar la rama $C$ |
| **5** | **C** | MIN | $[3, +\infty]$ | — | Entrada a $C$ antes de evaluar al hijo $G$ |
| **6** | **G** | MAX | $[3, +\infty]$ | — | Entrada a $G$ antes de evaluar la hoja $K$ (2) |
| **7** | **G** | MAX | $[3, +\infty]$ | 2 | $G$ mantiene $\alpha=3$ antes de evaluar $L$ (1). Devuelve 2 |
| **—** | **C** | MIN | — | — | **Poda Alfa en C**: como $2 \le 3$, **se descarta la hoja H (5)** |
| **8** | **A** | MAX | $[3, +\infty]$ | — | $A$ mantiene $\alpha=3$ antes de explorar la rama $D$ |
| **9** | **D** | MIN | $[3, +\infty]$ | — | Entrada a $D$ antes de evaluar la hoja $I$ (5) |
| **10** | **D** | MIN | $[3, 5]$ | — | $D$ actualiza $\beta=5$ antes de evaluar al hijo $J$ |
| **11** | **J** | MAX | $[3, 5]$ | — | Entrada a $J$ antes de evaluar la hoja $M$ (4) |
| **12** | **J** | MAX | $[4, 5]$ | — | $J$ actualiza $\alpha=4$ antes de evaluar la hoja $N$ (2) |
| **13** | **J** | MAX | $[4, 5]$ | 6 | $J$ mantiene $\alpha=4$ antes de evaluar $O$ (6) |
| **—** | **J** | MAX | — | — | **Poda Beta en J**: como $6 \ge 5$, **se descarta la hoja P (1)** |
| **Fin** | **A** | MAX | — | **5** | $D$ devuelve 5. $A$ elige **AD**. Jugador 2 responde con **DI** |

---

## 💻 Opción D: Salida literal de la consola (`demo_simple_game_tree.py`)

```text
A: [-inf, inf]
B: [-inf, inf]
B: [-inf, 4]
A: [3, inf]
C: [3, inf]
G: [3, inf]
G: [3, inf]
A: [3, inf]
D: [3, inf]
D: [3, 5]
J: [3, 5]
J: [4, 5]
J: [4, 5]

Game state before move:
A

Minimax value = 5
Player 'Minimax + alpha-beta 1' [Player 1] moves AD.

Game state before move:
D

Minimax value = -5
Player 'Minimax + alpha-beta 2' [Player 2] moves DI.

Game over.
Player Minimax + alpha-beta 1 [Player 1]: 5
Player Minimax + alpha-beta 2 [Player 2]: 0
```
