Our subscription checkout works like this. A customer starts checkout and we charge the card. If the charge fails we retry it, at most twice, and then the order fails. The customer can cancel at any time until the charge succeeds. The payment provider confirms a charge with a webhook, and that webhook can arrive late, after the customer cancelled.

The rule we care about: a cancelled order is never charged.

Check whether this flow keeps that rule, and show me the states. Keep your model files under `./model/`. Do not write application code.
