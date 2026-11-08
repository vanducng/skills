// Handles the card provider's "payment succeeded" webhook. The provider retries a delivery it did not see answered.
export async function onPaymentSucceeded(event, db, mail) {
  const order = await db.orders.find(event.orderId);
  if (order.status === "cancelled") return { status: 200 };
  await db.orders.update(order.id, { status: "paid", paidAt: event.createdAt });
  await db.charges.insert({ orderId: order.id, amount: event.amount, providerId: event.chargeId });
  await mail.sendReceipt(order.customerEmail, order.id);
  return { status: 200 };
}
