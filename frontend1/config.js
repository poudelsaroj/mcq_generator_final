// Set API URLs based on environment
const DEV_API_URL = 'http://192.168.1.16:8000'; // Your local IP
const NGROK_API_URL = 'https://d488-2407-1400-aa04-2a28-3d4d-bf74-6d4.ngrok-free.app'; // Your actual ngrok URL

export const getApiUrl = () => {
  // For development/testing, always use the ngrok URL to ensure consistent behavior
//   return NGROK_API_URL;
  
  // When you want to switch between local and ngrok:
  return __DEV__ ? DEV_API_URL : NGROK_API_URL;
};

export const getWebSocketUrl = () => {
  const baseUrl = getApiUrl();
  return baseUrl.replace('http', 'ws');
};