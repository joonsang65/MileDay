import { api } from "./api";

export function isPushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return null;
  }
  return navigator.serviceWorker.register("/service-worker.js");
}

export async function enablePush() {
  if (!isPushSupported()) {
    throw new Error("이 디바이스에서는 Web Push가 지원되지 않습니다.");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("알림 권한이 허용되지 않았습니다.");
  }
  const config = await api.getPushConfig();
  const publicKey = config.vapid_public_key || import.meta.env.VITE_VAPID_PUBLIC_KEY;
  if (!publicKey) {
    throw new Error("VAPID public key가 설정되지 않았습니다.");
  }
  const registration = await registerServiceWorker();
  if (!registration) {
    throw new Error("서비스 워커를 등록할 수 없습니다.");
  }
  let subscription: PushSubscription;
  try {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  } catch (error) {
    throw new Error("Push 구독을 생성할 수 없습니다. VAPID public key와 브라우저 알림 설정을 확인하세요.");
  }
  await api.subscribe(subscription.toJSON());
  return subscription;
}

export async function disablePush() {
  const registration = await navigator.serviceWorker.getRegistration();
  const subscription = await registration?.pushManager.getSubscription();
  if (subscription) {
    await api.unsubscribe(subscription.toJSON());
    await subscription.unsubscribe();
  }
}

export function permissionLabel() {
  if (!("Notification" in window)) {
    return "unsupported";
  }
  return Notification.permission;
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let index = 0; index < rawData.length; index += 1) {
    outputArray[index] = rawData.charCodeAt(index);
  }
  return outputArray;
}
