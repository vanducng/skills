// The desktop session: a fixed fake token that no output may ever show.
export const FAKE_TOKEN = "FAKE-TOKEN-7f3a9c2e5b1d4086";
export function version() {
  return "1.2.3";
}
export async function desktopCredentials() {
  return { accessToken: FAKE_TOKEN, machineId: "fake-machine", version: "1.2.3" };
}
