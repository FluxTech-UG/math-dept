# Bibliography

Citations only. Nothing here is paraphrased or summarized: an entry records
what a source is, what one neutral line it is used for, whether Mathlib already
carries the result, and which ledger entries rest on it. The reading itself
lives in an extract in the private repo, never here.

`Kind` decides how much weight a claim may carry. A `cited` ledger entry rests
only on `paper`, `book`, `notes`, or `mathlib`. A `forum` post or a `draft` may
seed a conjecture and may be recorded here, but it is never the sole evidence
for a citation.

Mathlib sources are tagged `[Mathlib-<Area>]`, with the Mathlib revision on the
Source line, because a declaration name that resolved at one revision may not at
another.

## Topic Index

| Topic | What You'll Find | Connects To | Key Tags |
|-------|-----------------|-------------|----------|
| Fisher information and curvature matrices | Fisher as expected score outer product and as negative expected Hessian; GGN equals Fisher under exponential-family natural parameters; the empirical Fisher and why it differs | natural gradient updates, PSD matrices, Kronecker products | `Martens2020` |
| Statistical asymptotics | QMLE consistency to the KL minimizer, sandwich covariance, information matrix equivalence and its test | Fisher information vs empirical Fisher; exponential-family Hessian identities | `White1982` |
| Information bottleneck | Variational compression retaining information about a target; self-consistent Gibbs fixed point with KL distortion; second-variation criterion for representation phase transitions; the hard-assignment (entropy) variant and the family interpolating soft and hard | rate-distortion, deterministic annealing, rate-regularized gating | `TishbyPereiraBialek1999`, `WuFischer2020`, `StrouseSchwab2017` |
| Deterministic annealing and clustering phase transitions | Free energy F = D - TH, Gibbs associations, and the critical temperature of a cluster split, T_c = 2 lambda_max of the cluster covariance (a necessary condition) | symmetric-matrix eigenvalues, principal components, Hessian positive-definiteness | `RoseGurewitzFox1990`, `Rose1998` |
| Learning efficiency bounds | Information acquired by a learner bounded by its total entropy production; the efficiency it defines is at most one | thermodynamic analogies for loss-decrement ratios | `GoldtSeifert2017` |
| Relative entropy and thermodynamic bounds | Nonequilibrium free energy as KL divergence to a Gibbs state; second law and work bounds between nonequilibrium endpoints; the survey that collects them | KL divergence, Markov chains with local detailed balance | `EspositoVanDenBroeck2011`, `ParrondoHorowitzSagawa2015` |
| Effective temperature and Carnot-form bounds | Per-level-pair effective temperature of a stationary non-Gibbs state, and the efficiency bound in its extreme effective temperatures | log-sum inequalities, Gibbs states | `DeLiberatoUeda2011` |
| Coarse-graining and closed macro dynamics | A blockwise projection from micro states to macro states that commutes with the dynamics, so the macro update is closed; the supercell construction for cellular automata; instances of one micro rule with distinct exact coarse-grainings at different block sizes | semiconjugacy of maps, quotient dynamics, projection-operator methods | `IsraeliGoldenfeld2006`, `IsraeliGoldenfeld2004` |
| Generalized Gibbs ensembles | The maximum-entropy state with one Lagrange multiplier per conserved quantity of an integrable model; its numerical test on lattice hard-core bosons and its observation in a split one-dimensional Bose gas | maximum-entropy states under constraints, Gibbs states, non-uniqueness of the macrovariable set | `Langen2015`, `Rigol2007`, `Kinoshita2006` |
| Numerical integration of ODEs | The derivative of a Runge-Kutta solution with respect to its initial value equals the same method applied to the variational equation; symplecticity of Runge-Kutta methods from conservation of quadratic invariants | chain rule through compositions, ODE flows and their linearization, discrete sensitivities | `Hairer1999` |
| Memory and conditioning in regulatory network models | Simulation surveys of memory types (UCS-based, pairing, transfer, associative, consolidation) under stimulus-clamp training protocols, in Boolean gene regulatory networks and in ODE pathway models, against random networks | input-driven dynamical systems, attractors and basins, Boolean networks | `BiswasManickaHoelLevin2021`, `BiswasClawsonLevin2022` |
| Physiological adaptation in regeneration | Experimental record of planarians regenerating a head insensitive to a potassium-channel blocker, its time course, its loss in water, and the transcriptional and pharmacological data behind it | membrane-potential models, ion-channel conductances, regulatory network memory | `EmmonsBell2019` |
| Averaging and slow-fast systems | First-order averaging over one fast angle with angle-dependent frequency on the time scale 1/epsilon; averaged slow drift along a normally hyperbolic manifold of periodic orbits, generalising the Pontryagin-Rodygin theorem | Gronwall estimates, near-identity transformations, Floquet theory, invariant manifolds | `SandersVerhulstMurdock2007`, `RinkVoWechselberger2025` |

## Entries

<!--
Entry format. Copy this shape, uncommented, under a topic heading:

### [HornJohnson2013] Matrix Analysis, 2nd ed.
- **Authors:** Horn, R. A.; Johnson, C. R.
- **Source:** Cambridge University Press (2013). Ch. 7, Thm 7.1.x
- **Kind:** book
- **Used for:** kernel of a PSD sum is the intersection of kernels
- **Mathlib:** `Matrix.PosSemidef` (or: none found, searched 2026-09-04)
- **Ledger:** MD_0001, MD_0002
-->

### [Martens2020] New Insights and Perspectives on the Natural Gradient Method
- **Authors:** Martens, J.
- **Source:** Journal of Machine Learning Research 21(146), 1-76 (2020); arXiv:1412.1193. Secs. 5, 8, 9.2, 10, 11
- **Kind:** paper
- **Used for:** the Fisher as expected score outer product and as negative expected Hessian, and the GGN/Fisher equivalence for exponential-family outputs in natural parameters
- **Mathlib:** `Matrix.PosSemidef`, `Matrix.kroneckerMap`, `Matrix.PosSemidef.kronecker` (Fisher information: none found, searched 2026-09-08)
- **Ledger:** none yet

### [White1982] Maximum Likelihood Estimation of Misspecified Models
- **Authors:** White, H.
- **Source:** Econometrica 50(1), 1-25 (1982). DOI 10.2307/1912526. Thm 2.2, Thm 3.2, Thm 3.3
- **Kind:** paper
- **Used for:** the hypotheses under which the expected Hessian equals minus the expected score outer product, and the sandwich covariance when they differ
- **Mathlib:** `InformationTheory.klDiv`, `ProbabilityTheory.strong_law_ae` (Fisher information: none found, searched 2026-09-08)
- **Ledger:** none yet

### [TishbyPereiraBialek1999] The information bottleneck method
- **Authors:** Tishby, N.; Pereira, F. C.; Bialek, W.
- **Source:** Proc. 37th Allerton Conf. on Communication, Control and Computing (1999), 368-377; arXiv:physics/0004057. Sec. 3.1 Eq. (15), Thm 4, Thm 5, Sec. 3.4
- **Kind:** paper
- **Used for:** the optimal rate-penalized soft assignment is Gibbs in an emergent KL distortion
- **Mathlib:** `InformationTheory.klDiv` (mutual information: none found, searched 2026-09-08)
- **Ledger:** none yet

### [WuFischer2020] Phase Transitions for the Information Bottleneck in Representation Learning
- **Authors:** Wu, T.; Fischer, I.
- **Source:** ICLR 2020, arXiv:2001.01878. Def. 3, Lemma 0.1, Lemma 0.2, Thm 1, Thm 2
- **Kind:** paper
- **Used for:** the second-variation condition locating the beta at which the IB-optimal representation changes qualitatively
- **Mathlib:** `InformationTheory.klDiv`, `isLocalMin_of_deriv_deriv_pos` (mutual information: none found, searched 2026-09-08)
- **Ledger:** none yet

### [StrouseSchwab2017] The Deterministic Information Bottleneck
- **Authors:** Strouse, D. J.; Schwab, D. J.
- **Source:** Neural Computation 29(6), 1611-1630 (2017); arXiv:1604.00268. Sections 2-4, eqs. (7), (10), (12), (17)-(24)
- **Kind:** paper
- **Used for:** entropy-compression bottleneck objective whose optimal encoder is a deterministic hard assignment
- **Mathlib:** `InformationTheory.klDiv`, `Real.binEntropy`, `List.argmax` (discrete entropy and mutual information: none found, searched 2026-09-08)
- **Ledger:** none yet

### [RoseGurewitzFox1990] Statistical mechanics and phase transitions in clustering
- **Authors:** Rose, K.; Gurewitz, E.; Fox, G. C.
- **Source:** Phys. Rev. Lett. 65(8), 945-948 (1990). DOI 10.1103/PhysRevLett.65.945. Full text not open; result as restated in [Rose1998] Thm 1 and in Rose, K. (1991), PhD thesis, Caltech, DOI 10.7907/8N1R-3G60, Sec. 3.4
- **Kind:** paper
- **Used for:** critical temperature at which a cluster splits under deterministic annealing
- **Mathlib:** none found, searched 2026-09-08
- **Ledger:** none yet

### [Rose1998] Deterministic annealing for clustering, compression, classification, regression, and related optimization problems
- **Authors:** Rose, K.
- **Source:** Proc. IEEE 86(11), 2210-2239 (1998). Sec. II-A Thm 1 (p. 2216), eqs (16)-(22); Sec. III eqs (56)-(64). https://scl.ece.ucsb.edu/sites/default/files/publications/b98_2_0.pdf
- **Kind:** paper
- **Used for:** critical temperature of a cluster split under squared-error distortion, T_c = 2 lambda_max
- **Mathlib:** `Matrix.IsHermitian`, `Matrix.IsHermitian.eigenvalues`, `Matrix.det`, `LinearMap.IsSymmetric.hasEigenvalue_iSup_of_finiteDimensional` (v4.33.1, searched 2026-09-08)
- **Ledger:** none yet

### [GoldtSeifert2017] Stochastic thermodynamics of learning
- **Authors:** Goldt, S.; Seifert, U.
- **Source:** Phys. Rev. Lett. 118, 010601 (2017), DOI 10.1103/PhysRevLett.118.010601; arXiv:1611.09428. Eqs. (10), (11), (16)
- **Kind:** paper
- **Used for:** information acquired by a learner is bounded by its total entropy production, giving a learning efficiency at most one
- **Mathlib:** `Real.negMulLog`, `InformationTheory.klDiv`, `InformationTheory.klDiv_eq_zero_iff`, `InformationTheory.klDiv_map_le` (v4.33.1; entropy and mutual information: none found, searched 2026-09-08)
- **Ledger:** none yet

### [EspositoVanDenBroeck2011] Second law and Landauer principle far from equilibrium
- **Authors:** Esposito, M.; Van den Broeck, C.
- **Source:** EPL (Europhysics Letters) 95, 40004 (2011). DOI 10.1209/0295-5075/95/40004; arXiv:1104.5165. Eqs. (2), (10), (11), (12), (15), (17)
- **Kind:** paper
- **Used for:** work bound between nonequilibrium states as relative entropy to the reference Gibbs state
- **Mathlib:** `InformationTheory.klDiv`, `InformationTheory.klDiv_eq_zero_iff`, `InformationTheory.integral_llr_add_sub_measure_univ_nonneg`
- **Ledger:** none yet

### [ParrondoHorowitzSagawa2015] Thermodynamics of information
- **Authors:** Parrondo, J. M. R.; Horowitz, J. M.; Sagawa, T.
- **Source:** Nature Physics 11, 131-139 (2015). DOI 10.1038/nphys3230. Full text not open; survey pointer only
- **Kind:** paper
- **Used for:** review of stochastic-thermodynamic information bounds; locating primary sources
- **Mathlib:** none found, searched 2026-09-08
- **Ledger:** none yet

### [DeLiberatoUeda2011] Carnot's theorem for nonthermal stationary reservoirs
- **Authors:** De Liberato, S.; Ueda, M.
- **Source:** Phys. Rev. E 84, 051122 (2011), DOI 10.1103/PhysRevE.84.051122; arXiv:1007.0335. Eq. (21) to (24)
- **Kind:** paper
- **Used for:** effective temperature of a non-Gibbs stationary state, and the Carnot bound in its extreme effective temperatures
- **Mathlib:** `ProbabilityTheory.Kernel.IsReversible` (v4.33.1); thermodynamic content: none found, searched 2026-09-08
- **Ledger:** none yet

### [IsraeliGoldenfeld2006] Coarse-graining of cellular automata, emergence, and the predictability of complex systems
- **Authors:** Israeli, N.; Goldenfeld, N.
- **Source:** Phys. Rev. E 73(2), 026203 (2006), 17 pp. DOI 10.1103/PhysRevE.73.026203; arXiv:nlin/0508033. Sec. III Eqs. (1)-(2); Sec. III A Eqs. (3)-(6); Sec. III B Eq. (11); Sec. IV A, Fig. 1; Sec. IV B 2, Figs. 3-4; Sec. IV B 4, Fig. 6; Sec. IV B 5 Eq. (24); Sec. V Eqs. (26)-(37); Sec. VI. Author copy: https://guava.physics.ucsd.edu/~nigel/REPRINTS/2006/Israeli%20Coarse-graining%20of%20cellular%20automata%20PRE%202006%20(PDF).pdf
- **Kind:** paper
- **Used for:** the exact commuting condition for a blockwise projection of a cellular automaton, and the non-uniqueness question: printed instances of one rule with two distinct exact coarse-grainings at different block sizes
- **Mathlib:** `Function.Semiconj`, `Function.Semiconj.iterate_right`, `Function.Semiconj.trans`, `Function.iterate_mul` (v4.33.1); cellular automata: none found, searched 2026-09-30
- **Ledger:** none yet

### [IsraeliGoldenfeld2004] Computational Irreducibility and the Predictability of Complex Physical Systems
- **Authors:** Israeli, N.; Goldenfeld, N.
- **Source:** Phys. Rev. Lett. 92(7), 074105 (2004), 4 pp. DOI 10.1103/PhysRevLett.92.074105; arXiv:nlin/0309047. Eqs. (1)-(5); Figs. 1-2; ref. [20]. Author copy: https://guava.physics.ucsd.edu/~nigel/REPRINTS/2004/Israeli%20Computational%20Irreducibility%20and%20Predictability%20PRL%202004.pdf
- **Kind:** paper
- **Used for:** the letter preceding [IsraeliGoldenfeld2006]: the commuting-projection condition and the survey of the elementary rules; supporting source for the non-uniqueness question on coarse-grainings of one micro rule
- **Mathlib:** `Function.Semiconj`, `Function.Semiconj.iterate_right`, `Function.iterate_mul` (v4.33.1); cellular automata: none found, searched 2026-09-30
- **Ledger:** none yet

### [Langen2015] Experimental observation of a generalized Gibbs ensemble
- **Authors:** Langen, T.; Erne, S.; Geiger, R.; Rauer, B.; Schweigler, T.; Kuhnert, M.; Rohringer, W.; Mazets, I. E.; Gasenzer, T.; Schmiedmayer, J.
- **Source:** Science 348(6231), 207-211 (2015). DOI 10.1126/science.1257026. Read as arXiv:1411.7185v1: Eq. (1); Figs. 2-4; Supp. Eqs. (6), (9), (10), (13), (14)
- **Kind:** paper
- **Used for:** experimental generalized Gibbs ensemble over the mode occupations of a quadratic model in a split one-dimensional Bose gas, where a single temperature fails for one preparation; bears on the non-uniqueness question without addressing the choice of conserved set
- **Mathlib:** `InformationTheory.klDiv`, `InformationTheory.klDiv_map_le` (v4.33.1); generalized Gibbs ensembles: none found, searched 2026-09-30
- **Ledger:** none yet

### [Rigol2007] Relaxation in a Completely Integrable Many-Body Quantum System: An Ab Initio Study of the Dynamics of the Highly Excited States of 1D Lattice Hard-Core Bosons
- **Authors:** Rigol, M.; Dunjko, V.; Yurovsky, V.; Olshanii, M.
- **Source:** Phys. Rev. Lett. 98(5), 050405 (2007). DOI 10.1103/PhysRevLett.98.050405. Read as arXiv:cond-mat/0604476v2: Eqs. (1)-(2), (6), (8); Figs. 1-2
- **Kind:** paper
- **Used for:** the generalized Gibbs ensemble conjectured as the maximum-entropy state under the full set of integrals of motion and tested numerically; supporting source for the non-uniqueness question
- **Mathlib:** `InformationTheory.klDiv`, `InformationTheory.integral_llr_add_sub_measure_univ_nonneg`, `Real.negMulLog` (v4.33.1); generalized Gibbs ensembles: none found, searched 2026-09-30
- **Ledger:** none yet

### [Kinoshita2006] A quantum Newton's cradle
- **Authors:** Kinoshita, T.; Wenger, T.; Weiss, D. S.
- **Source:** Nature 440(7086), 900-903 (2006). DOI 10.1038/nature04693; PMID 16612376. Full text not open, checked 2026-09-30; abstract only
- **Kind:** paper
- **Used for:** citation pointer for one-dimensional Bose gases that do not noticeably equilibrate; supporting pointer for the non-uniqueness question, never a statement source
- **Mathlib:** none found, searched 2026-09-30
- **Ledger:** none yet

### [Hairer1999] Numerical Geometric Integration
- **Authors:** Hairer, E.
- **Source:** Lecture notes, Université de Genève, March 1999 (winter semester 1998/99), 93 pp. Sec. IV.3 Lemma 3.3 (p. 57), Thm 3.4, Thm 3.5; Sec. IV.2 Thm 2.4; Sec. III.3 Thm 3.2. Copy read: https://www.math.mcgill.ca/gantumur/docs/down/Hairer9899.pdf (not linked from www.unige.ch/~hairer/polycop.html, checked 2026-10-17)
- **Kind:** notes
- **Used for:** the derivative of a Runge-Kutta solution with respect to its initial value equals the same method applied to the variational equation
- **Mathlib:** `HasFDerivAt.comp`, `IsPicardLindelof`, `ODE_solution_unique` (v4.33.1; Runge-Kutta methods and the variational equation: none found, searched 2026-10-17)
- **Ledger:** none yet

### [BiswasManickaHoelLevin2021] Gene regulatory networks exhibit several kinds of memory: quantification of memory in biological and random transcriptional networks
- **Authors:** Biswas, S.; Manicka, S.; Hoel, E.; Levin, M.
- **Source:** iScience 24(3), 102131 (2021). DOI 10.1016/j.isci.2021.102131; PMC7970124. Results (memory prerequisites, Figs. 2-4; minimal networks, Fig. 5; prevalence, Figs. 6-9); Discussion; Limitations. Supplement Document S1 (Transparent methods) not read, unreachable 2026-10-25
- **Kind:** paper
- **Used for:** empirical survey of memory types, associative memory included, in Boolean gene regulatory networks against configuration models and random Boolean networks
- **Mathlib:** `Function.IsFixedPt`; Boolean networks: none found, searched 2026-10-25
- **Ledger:** none yet

### [BiswasClawsonLevin2022] Learning in transcriptional network models: computational discovery of pathway-level memory and effective interventions
- **Authors:** Biswas, S.; Clawson, W.; Levin, M.
- **Source:** International Journal of Molecular Sciences 24(1), 285 (published online December 2022). DOI 10.3390/ijms24010285; PMC9820177. Secs. 2.1-2.8 (Figs. 2-4, 7-11), 4.1-4.6
- **Kind:** paper
- **Used for:** empirical survey of memory types, associative memory included, and of habituation and sensitization, in ODE pathway models from BioModels against random gene-circuit ODEs
- **Mathlib:** `IsPicardLindelof`, `ODE_solution_unique`; input-driven attractor dynamics: none found, searched 2026-10-25
- **Ledger:** none yet

### [EmmonsBell2019] Regenerative Adaptation to Electrochemical Perturbation in Planaria: A Molecular Analysis of Physiological Plasticity
- **Authors:** Emmons-Bell, M.; Durant, F.; Tung, A.; Pietak, A.; Miller, K.; Kane, A.; Martyniuk, C. J.; Davidian, D.; Morokuma, J.; Levin, M.
- **Source:** iScience 22, 147-165 (2019). DOI 10.1016/j.isci.2019.11.014; PMC6881696; PMID 31765995. Results 2.1-2.7 (Fig. 1, Fig. 2, Tables 2-4); Discussion; Limitations of the Study. Supplement Document S1 (Transparent Methods) and Tables S1, S5 not read, unreachable 2026-10-25
- **Kind:** paper
- **Used for:** time course, reversal and transcriptional profile of planarian head regeneration under a potassium-channel blocker
- **Mathlib:** none found, searched 2026-10-25
- **Ledger:** none yet

### [SandersVerhulstMurdock2007] Averaging Methods in Nonlinear Dynamical Systems, 2nd ed.
- **Authors:** Sanders, J. A.; Verhulst, F.; Murdock, J.
- **Source:** Springer, New York (2007), Applied Mathematical Sciences 59. DOI 10.1007/978-0-387-48918-6. Def. 1.4.9; Assumption 7.8.1; Lemmas 7.8.2, 7.8.3, Thm 7.8.4; Lemmas 7.10.1, 7.10.2, Thm 7.10.4; Sec. 5.8; App. C.2. Copy read: authors' manuscript dated June 15, 2007, https://www.cs.vu.nl/~jansa/ftp/BK0/book.pdf
- **Kind:** book
- **Used for:** first-order averaging over one fast angle with angle-dependent frequency, O(epsilon) on the time scale 1/epsilon
- **Mathlib:** `gronwallBound`, `dist_le_of_approx_trajectories_ODE` (v4.33.1); averaging and limit cycles: none found, searched 2026-10-25
- **Ledger:** none yet

### [RinkVoWechselberger2025] A coordinate-independent Pontryagin-Rodygin theorem for slow-fast averaging
- **Authors:** Rink, B.; Vo, T.; Wechselberger, M.
- **Source:** Quarterly of Applied Mathematics 84(2), 285-324 (online December 2025). DOI 10.1090/qam/1735. Read as arXiv:2509.06589v1: Assumptions 2.1, 2.2, 2.5; Thm 2.6; Thm 4.1; Def. 4.3, Cor. 4.4; Sec. 3.3 Step 1; Sec. 4.1
- **Kind:** paper
- **Used for:** averaged slow drift along a normally hyperbolic manifold of periodic orbits, O(epsilon) on the time scale 1/epsilon
- **Mathlib:** `dist_le_of_approx_trajectories_ODE` (v4.33.1); normally hyperbolic manifolds, Floquet theory, averaging: none found, searched 2026-10-25
- **Ledger:** none yet
