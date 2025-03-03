import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system';
import NetInfo from '@react-native-community/netinfo';

// Export this function so it can be imported in other files
export const getBaseUrl = () => {
  // Use the direct IP address for all platforms
  return 'http://192.168.1.16:8000'; // Replace with your actual machine's IP address
};

// Get WebSocket URL based on environment
const getWebSocketUrl = () => {
  // Use the direct IP address for WebSocket connections too
  return 'ws://192.168.1.16:8000'; // Replace with your actual machine's IP address
};

// WebSocket connection management
export class WebSocketService {
  constructor() {
    this.ws = null;
    this.clientId = Math.random().toString(36).substring(2, 15);
    this.callbacks = {
      onOpen: null,
      onMessage: null,
      onError: null,
      onClose: null,
      onStatus: null,
    };
  }

  connect() {
    const wsUrl = `${getWebSocketUrl()}/api/ws/${this.clientId}`;
    console.log('Connecting to WebSocket:', wsUrl);

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = (event) => {
      console.log('WebSocket connection established');
      if (this.callbacks.onOpen) this.callbacks.onOpen(event);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        
        // Handle status updates
        if (data.status && this.callbacks.onStatus) {
          this.callbacks.onStatus(data.status, data.message);
        }
        
        // Pass full message to general handler
        if (this.callbacks.onMessage) this.callbacks.onMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (this.callbacks.onError) this.callbacks.onError(error);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket connection closed:', event.code, event.reason);
      if (this.callbacks.onClose) this.callbacks.onClose(event);
      this.ws = null;
    };

    return this;
  }

  disconnect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }

  sendMessage(message) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return false;
    }
    
    this.ws.send(JSON.stringify(message));
    return true;
  }

  setCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
    return this;
  }
}

// Create WebSocket instance for file processing
export function processFileWithWebSocket(fileUri, fileName, fileType, documentType = 'document') {
  return new Promise(async (resolve, reject) => {
    try {
      // Read file as base64
      const base64Data = await FileSystem.readAsStringAsync(fileUri, {
        encoding: FileSystem.EncodingType.Base64
      });
      
      console.log(`File read as base64, length: ${base64Data.length}`);
      
      // Create and connect WebSocket
      const wsService = new WebSocketService();
      
      wsService.setCallbacks({
        onOpen: () => {
          console.log('WebSocket opened, sending file processing command');
          // Send the file processing command once connected
          wsService.sendMessage({
            command: 'process_file',
            file_content: base64Data,
            file_name: fileName,
            file_type: fileType,
            document_type: documentType
          });
        },
        onMessage: (data) => {
          if (data.status === 'complete') {
            // Successfully processed file
            console.log('File processing completed');
            wsService.disconnect();
            resolve(data);
          } else if (data.status === 'error') {
            // Error processing file
            console.error('Error from server:', data.message);
            wsService.disconnect();
            reject(new Error(data.message || 'Error processing file'));
          }
        },
        onError: (error) => {
          console.error('WebSocket error:', error);
          reject(new Error('WebSocket error: Connection failed'));
          wsService.disconnect();
        },
        onClose: (event) => {
          if (event.code !== 1000) {
            console.error('WebSocket closed abnormally:', event.code, event.reason);
            reject(new Error(`WebSocket closed unexpectedly: ${event.reason || 'Unknown reason'}`));
          }
        },
        onStatus: (status, message) => {
          console.log(`Processing status: ${status} - ${message || ''}`);
        }
      }).connect();

      // Add timeout to prevent hanging forever
      setTimeout(() => {
        if (wsService.ws && wsService.ws.readyState === WebSocket.OPEN) {
          wsService.disconnect();
          reject(new Error('File processing timed out after 60 seconds'));
        }
      }, 60000);
    } catch (error) {
      console.error('Error in WebSocket file processing:', error);
      reject(error);
    }
  });
}

export async function generateMCQsFromAPI(content, numQuestions = 5) {
  // Check network connection first
  const networkState = await NetInfo.fetch();
  if (!networkState.isConnected) {
    throw new Error('No internet connection. Please check your network and try again.');
  }
  
  console.log('Sending request to API:', { 
    endpoint: `${getBaseUrl()}/generate-mcqs`,
    payload_preview: content.substring(0, 50) + '...',
    num_questions: numQuestions 
  });
  
  try {
    // Increase timeout for model computation (MCQ generation can take time)
    const timeout = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Request timeout after 60 seconds')), 60000)
    );
    
    // Add debugging info in request
    console.log('Full request URL:', `${getBaseUrl()}/generate-mcqs`);
    console.log('Request body:', {
      text: content.substring(0, 100) + '...',
      num_questions: numQuestions
    });
    
    const fetchPromise = fetch(`${getBaseUrl()}/generate-mcqs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        text: content,
        num_questions: numQuestions,
      }),
    });

    // Race between fetch and timeout
    const response = await Promise.race([fetchPromise, timeout]);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
      throw new Error(`Server error (${response.status}): ${errorText || 'Unknown error'}`);
    }

    const data = await response.json();
    console.log('API response received successfully:', data);
    
    // Return the mcqs array directly - this is the key change
    return data.mcqs || [];
  } catch (error) {
    console.error('Network or API error:', error);
    
    if (error.message.includes('timeout')) {
      throw new Error('The server took too long to respond. Try with a shorter text or fewer questions.');
    } else if (error.message.includes('Network request failed')) {
      throw new Error('Cannot connect to server. Please check if the server is running and try again.');
    }
    
    throw new Error(`Connection error: ${error.message}`);
  }
}

export async function generateAssessmentFromAPI(content, numQuestions = 5) {
  return generateMCQsFromAPI(content, numQuestions);
}

export async function processFileAPI(fileUri, fileName, fileType, documentType = 'document') {
  console.log('Processing file with API:', { fileName, fileType, documentType });
  
  // Always use WebSocket for large files and more complex processing
  if (fileType.includes('pdf') || fileType.includes('image') || documentType === 'book') {
    return await processFileWithWebSocket(fileUri, fileName, fileType, documentType);
  }
  
  // Fallback to HTTP for simpler files
  try {
    const base64Data = await FileSystem.readAsStringAsync(fileUri, {
      encoding: FileSystem.EncodingType.Base64
    });
    
    const response = await fetch(`${getBaseUrl()}/process-file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_content: base64Data,
        file_name: fileName,
        file_type: fileType,
        document_type: documentType
      }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
      throw new Error(`Server responded with status ${response.status}: ${errorText || 'Unknown error'}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error processing file:', error);
    throw new Error('Failed to process file. Please check your file format and try again.');
  }
}

export async function generateMCQsFromFileAPI(fileUri, fileName, fileType, numQuestions) {
  console.log('Generating MCQs from file:', { fileName, fileType, numQuestions });
  
  try {
    // Read file as base64
    const base64Data = await FileSystem.readAsStringAsync(fileUri, {
      encoding: FileSystem.EncodingType.Base64
    });
    
    const response = await fetch(`${getBaseUrl()}/generate-mcqs-from-file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_content: base64Data,
        file_name: fileName,
        file_type: fileType,
        num_questions: numQuestions
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
      throw new Error(`Server responded with status ${response.status}: ${errorText || 'Unknown error'}`);
    }

    const data = await response.json();
    return data.mcqs;
  } catch (error) {
    console.error('Error generating MCQs from file:', error);
    throw new Error('Failed to generate MCQs from file. Please check your connection and try again.');
  }
}

export async function testServerConnection() {
  try {
    const response = await fetch(`${getBaseUrl()}/health`, { 
      method: 'GET',
      timeout: 5000 // 5 second timeout for quick check
    });
    
    if (response.ok) {
      return { connected: true, message: 'Server is reachable' };
    } else {
      return { connected: false, message: `Server returned status ${response.status}` };
    }
  } catch (error) {
    console.error('Server connection test failed:', error);
    return { 
      connected: false, 
      message: 'Cannot connect to server',
      error: error.message 
    };
  }
}

export const processFileWithOCR = async (fileUri, fileName, fileType) => {
  try {
    console.log('Processing file with OCR:', { fileName, fileType });
    
    // Read file as base64
    const base64Data = await FileSystem.readAsStringAsync(fileUri, {
      encoding: FileSystem.EncodingType.Base64
    });
    
    const response = await fetch(`${API_BASE_URL}/process-file-ocr`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_content: base64Data,
        file_name: fileName,
        file_type: fileType,
        force_ocr: true  // This explicitly tells the backend to use OCR
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('OCR API Error:', response.status, errorText);
      throw new Error(`Server responded with status ${response.status}: ${errorText || 'Unknown error'}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error processing file with OCR:', error);
    throw new Error('Failed to process file with OCR. Please try again.');
  }
};