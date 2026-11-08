<!-- From the upstream statechart skill (MIT, see ../LICENSE.txt); moved here from SKILL.md unchanged except headings. -->

# Write the spec

- Write each rule that the reader agrees to as an INVARIANT. A rule can be about a screen, a result, a stored value, or a message. If the model has no variable for a rule, add the variable. Never weaken a rule to make it hold.
- Write `Next` as a disjunction of the actions, such as `YouPressPlay \/ YouPressStop`. If you do not, TLC names every step `Next`.
- A state with no step out breaks `NoDeadlock`, also when it is a correct end state. When an INVARIANT or a PROPERTY already has that name, the rule is `CHECK_DEADLOCK`. Add to `Next` an action that is true only in the end states and changes nothing, such as `Done == phase \in {"paid", "failed"} /\ UNCHANGED vars`, and give it a label in `step()`.
