const saved = [];
const validate = order => { if (!order.id) throw new Error("no id"); return order; };
const save = order => { saved.push(order); return order; };
// DO NOT REORDER: validate must run before save, or an order with no id is saved.
const steps = [validate, save];
const run = order => steps.reduce((o, step) => step(o), order);
module.exports = { run, steps, validate, save, saved };
