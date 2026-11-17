# Engineering use

The claims board marks whether a claim has a **candidate engineering use**: a test against real engineering data that
could be run now. This is the maintainer's assessment of each problem's subject, not a fact about the proof, and it is
meant to be argued with. Acceptance is earned in slices: a machine checks that a proof is valid; a person judges
whether the statement says what was asked; an application shows where the result holds in use. This column is about
that last slice. A result with no foreseen use is not worth less. Its acceptance comes from mathematicians reusing it.

| claim | candidate? | why |
|---|---|---|
| Erdős #1133 | yes | A low-degree polynomial that matches most of a set of bounded data values must blow up somewhere on [-1, 1]. That bounds how far an outlier-tolerant polynomial fit, a polynomial surrogate model or a spectral method on Chebyshev grids can go wrong between nodes. Test: fit polynomial surrogates to a real sensor series with injected outliers and compare the blow-up with the claim's rates. Needs explicit constants at practical degrees. |
| Erdős #671 | yes | Some node arrays make interpolation unstable at every point, yet each continuous function's interpolants converge at some point: agreement at checked points certifies nothing about stability elsewhere. Test the lesson, not the theorem, on collocation points of a physics-informed network or a spectral solver. |
| Erdős #550 | no | A Ramsey bound for large trees against complete multipartite graphs. A network-design reading is conceivable but no design problem takes this form today. |
| Erdős #306, #731, #768, #856, #1061 | no | Number theory: unit fractions, divisibility of binomial coefficients, densities, lcm-free sets, the divisor-sum function. |
| Erdős #593, #1177 | no | Infinite combinatorics and set theory. |
| Prime gaps ≤ 186, ≤ 240 | no | No deployed system depends on bounded gaps between primes. |

To propose a use, open an issue with the data you would test against.
