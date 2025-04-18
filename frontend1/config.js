// Set API URLs based on environment
const DEV_API_URL = 'http://192.168.1.4:8000';
const NGROK_API_URL = 'https://71e5-113-199-225-138.ngrok-free.app'; // Your actual ngrok URL

export const getApiUrl = () => {
  // For development/testing, always use the ngrok URL to ensure consistent behavior
  // return NGROK_API_URL;

  // When you want to switch between local and ngrok:
  return __DEV__ ? DEV_API_URL : NGROK_API_URL;
};

export const getWebSocketUrl = () => {
  const baseUrl = getApiUrl();
  return baseUrl.replace('https', 'wss').replace('http', 'ws');};