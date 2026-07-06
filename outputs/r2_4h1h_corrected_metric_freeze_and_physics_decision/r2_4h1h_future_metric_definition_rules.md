# R2-4H1H future metric-definition rules

Future 2D far-field angular metrics must use a documented angle vector from `farfieldangle` or an equivalent extracted theta grid.

Future eta/leakage integrations must use one consistent total-normalized definition. Preferred choices are an official `farfield2dintegrate`-like window integration or explicit weighted numerical integration over theta.

Every report must state whether each angular window is disjoint or cumulative, signed or absolute-angle, one-sided or two-sided. Future reports must not mix the original H1F leakage definitions with the H1G/H1H corrected definitions.
