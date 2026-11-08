Billing reports: "Some customers are charged twice. The card provider retries its 'payment succeeded' webhook when we answer slowly, and each delivery marks the order paid and sends the receipt again." The webhook handler is in `src/webhook.js`.

Take this in as a work item. Do not fix the code yet. This directory is not an OpenRig rig: do not run `rig`. The workbench skill's resolver is `node tools/records.cjs`.
