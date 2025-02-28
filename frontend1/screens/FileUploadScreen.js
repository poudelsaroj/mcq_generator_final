import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator,
  Animated, Easing, Modal
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import { WebSocketService, processFileAPI } from '../services/apiService';

const SERVER_URL = '192.168.1.16:8000'; // Update with your actual server IP

const FileUploadScreen = ({ navigation }) => {
  const [fileName, setFileName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [fileUri, setFileUri] = useState('');
  const [processingStatus, setProcessingStatus] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileType, setFileType] = useState('');
  const [documentType, setDocumentType] = useState('document'); // 'document' or 'book'
  const [showBookOptions, setShowBookOptions] = useState(false);
  const spinValue = useRef(new Animated.Value(0)).current;
  
  // Generate a unique client ID for this session
  const clientId = useRef(Math.random().toString(36).substring(2, 15)).current;
  // WebSocket connection reference
  const ws = useRef(null);

  // Initialize WebSocket connection
  useEffect(() => {
    // Only connect WebSocket when needed
    if (isLoading) {
      connectWebSocket();
    }
    
    return () => {
      // Clean up WebSocket on unmount
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, [isLoading]);

  // Animation for loading spinner
  useEffect(() => {
    if (isLoading) {
      Animated.loop(
        Animated.timing(spinValue, {
          toValue: 1,
          duration: 1500,
          easing: Easing.linear,
          useNativeDriver: true
        })
      ).start();
    } else {
      spinValue.setValue(0);
    }
  }, [isLoading]);

  // Connect to WebSocket
  const connectWebSocket = () => {
    try {
      ws.current = new WebSocket(`ws://${SERVER_URL}/api/ws/${clientId}`);
      
      ws.current.onopen = () => {
        console.log('WebSocket connection established');
      };
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.percentage !== undefined) {
          setUploadProgress(data.percentage);
        }
        if (data.status) {
          setProcessingStatus(data.status);
        }
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      ws.current.onclose = () => {
        console.log('WebSocket connection closed');
      };
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
    }
  };

  // Upload file with progress tracking
  const uploadPdfFile = async (uri) => {
    try {
      setIsLoading(true);
      
      // Create form data for file upload
      const formData = new FormData();
      formData.append('file', {
        uri: uri,
        type: 'application/pdf',
        name: uri.split('/').pop()
      });
      
      // Send the request with the client_id as a query parameter
      const response = await fetch(`http://${SERVER_URL}/api/extract-text?client_id=${clientId}`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }
      
      // Parse the response
      const data = await response.json();
      
      // Read file content as base64
      const fileContent = await FileSystem.readAsStringAsync(fileUri, { encoding: 'base64' });
      
      // Navigate to NumQuestionsScreen with the file content
      navigation.navigate('NumQuestions', { fileContent });
    } catch (error) {
      console.error('File upload error:', error);
      Alert.alert('Error', `Failed to process file: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilePick = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
          'text/plain',
          'image/jpeg',
          'image/png'
        ],
        copyToCacheDirectory: true
      });

      if (result.canceled) {
        console.log('User cancelled document picker');
        return;
      }

      const { uri, name, mimeType } = result.assets[0];
      setFileUri(uri);
      setFileName(name);
      setFileType(mimeType || '');
      console.log('File selected:', { name, mimeType });
    } catch (error) {
      console.error('Error picking document:', error);
      Alert.alert('Error', 'Failed to select document');
    }
  };
  
  const handleUpload = async () => {
    if (!fileUri) {
      Alert.alert('Error', 'Please select a file first');
      return;
    }
    
    setIsLoading(true);
    setProcessingStatus('Connecting...');
    
    try {
      // Process file with API (this will use WebSocket for large files)
      const result = await processFileAPI(fileUri, fileName, fileType, documentType);
      
      // Handle result based on book or document
      if (result.is_book && result.chapters && result.chapters.length > 1) {
        // Show book options or go to chapter selection
        if (documentType === 'book') {
          setShowBookOptions(true);
        } else {
          navigation.navigate('ChapterSelection', {
            chapters: result.chapters,
            fileName: fileName
          });
        }
      } else {
        // Regular document - navigate to questions screen
        const content = result.chapters[0].content;
        navigation.navigate('NumQuestions', {
          contentType: 'text',
          content: content
        });
      }
    } catch (error) {
      console.error('Error processing file:', error);
      Alert.alert('Error', error.message || 'Failed to process file');
    } finally {
      setIsLoading(false);
      setProcessingStatus('');
    }
  };
  
  const processDocument = async (processWholeBook = false) => {
    setIsLoading(true);
    try {
      // Add document_type to the API call
      const result = await processFileAPI(fileUri, fileName, fileType, documentType);
      
      if (result.is_book && result.chapters.length > 1 && !processWholeBook) {
        // It's a book with multiple chapters - navigate to chapter selection
        navigation.navigate('ChapterSelection', {
          chapters: result.chapters,
          fileName: fileName
        });
      } else {
        // It's a regular document or whole book processing - navigate directly to question number selection
        let content;
        
        if (processWholeBook && result.chapters && result.chapters.length > 0) {
          // Combine all chapter contents for whole book processing
          content = result.chapters.map(chapter => chapter.content).join('\n\n');
        } else {
          // Just use the first chapter/content
          content = result.chapters[0].content;
        }
        
        navigation.navigate('NumQuestions', {
          contentType: 'text',
          content: content
        });
      }
    } catch (error) {
      console.error('Error processing file:', error);
      Alert.alert('Error', error.message || 'Failed to process file');
    } finally {
      setIsLoading(false);
      setShowBookOptions(false);
    }
  };

  const renderFileIcon = () => {
    if (fileType.includes('pdf')) {
      return <Ionicons name="document-text" size={48} color="#FF5252" />;
    } else if (fileType.includes('word')) {
      return <Ionicons name="document-text" size={48} color="#4285F4" />;
    } else if (fileType.includes('presentation')) {
      return <Ionicons name="easel" size={48} color="#FF9800" />;
    } else if (fileType.includes('text')) {
      return <Ionicons name="document" size={48} color="#424242" />;
    } else if (fileType.includes('image')) {
      return <Ionicons name="image" size={48} color="#4CAF50" />;
    }
    return <Ionicons name="document" size={48} color="#757575" />;
  };

  // Transform rotation value to degrees
  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg']
  });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Upload Document</Text>
      <Text style={styles.subtitle}>
        Upload a PDF, DOCX, PPT, TXT, or image file to generate MCQs
      </Text>
      
      <TouchableOpacity 
        style={styles.uploadArea} 
        onPress={handleFilePick}
        disabled={isLoading}
      >
        {fileUri ? (
          <View style={styles.fileInfoContainer}>
            {renderFileIcon()}
            <Text style={styles.fileName}>{fileName}</Text>
            <TouchableOpacity
              style={styles.changeButton}
              onPress={handleFilePick}
              disabled={isLoading}
            >
              <Text style={styles.changeButtonText}>Change File</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            <Ionicons name="cloud-upload" size={64} color="#007AFF" />
            <Text style={styles.uploadText}>Tap to select document</Text>
            <Text style={styles.supportedFormatsText}>
              Supported formats: PDF, DOCX, PPT, TXT, PNG, JPG
            </Text>
          </>
        )}
      </TouchableOpacity>

      <View style={styles.documentTypeContainer}>
        <Text style={styles.documentTypeLabel}>Document Type:</Text>
        <View style={styles.documentTypeButtons}>
          <TouchableOpacity
            style={[
              styles.documentTypeButton,
              documentType === 'document' && styles.documentTypeSelected
            ]}
            onPress={() => setDocumentType('document')}
            disabled={isLoading}
          >
            <Ionicons 
              name="document-text" 
              size={24} 
              color={documentType === 'document' ? "#fff" : "#007AFF"} 
            />
            <Text 
              style={[
                styles.documentTypeText,
                documentType === 'document' && styles.documentTypeTextSelected
              ]}
            >
              Document
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[
              styles.documentTypeButton,
              documentType === 'book' && styles.documentTypeSelected
            ]}
            onPress={() => setDocumentType('book')}
            disabled={isLoading}
          >
            <Ionicons 
              name="book" 
              size={24} 
              color={documentType === 'book' ? "#fff" : "#007AFF"} 
            />
            <Text 
              style={[
                styles.documentTypeText,
                documentType === 'book' && styles.documentTypeTextSelected
              ]}
            >
              Book
            </Text>
          </TouchableOpacity>
        </View>
      </View>
      
      <TouchableOpacity
        style={[
          styles.continueButton,
          (!fileUri || isLoading) && styles.disabledButton
        ]}
        onPress={handleUpload}
        disabled={!fileUri || isLoading}
      >
        {isLoading ? (
          <ActivityIndicator color="#fff" size="small" />
        ) : (
          <>
            <Text style={styles.buttonText}>Continue</Text>
            <Ionicons name="arrow-forward" size={20} color="#fff" />
          </>
        )}
      </TouchableOpacity>
      
      {isLoading && (
        <Text style={styles.loadingText}>
          Processing document... This may take a moment.
        </Text>
      )}

      {/* Book processing options modal */}
      <Modal
        visible={showBookOptions}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowBookOptions(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Book Processing Options</Text>
            <Text style={styles.modalSubtitle}>How would you like to process this book?</Text>
            
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => processDocument(true)} // Process whole book
            >
              <Ionicons name="book-outline" size={24} color="#007AFF" />
              <View style={styles.modalOptionTextContainer}>
                <Text style={styles.modalOptionTitle}>Process Entire Book</Text>
                <Text style={styles.modalOptionDescription}>
                  Generate questions from the entire book content
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#007AFF" />
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => processDocument(false)} // Process chapter by chapter
            >
              <Ionicons name="list-outline" size={24} color="#007AFF" />
              <View style={styles.modalOptionTextContainer}>
                <Text style={styles.modalOptionTitle}>Select Specific Chapters</Text>
                <Text style={styles.modalOptionDescription}>
                  Choose which chapters to include
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#007AFF" />
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.modalCancelButton}
              onPress={() => setShowBookOptions(false)}
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  uploadCard: {
    width: '100%',
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  uploadButton: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  uploadText: {
    marginTop: 10,
    fontSize: 16,
    color: '#007AFF',
    textAlign: 'center',
  },
  helperText: {
    marginTop: 20,
    color: '#666',
    textAlign: 'center',
  },
  fileInfoContainer: {
    marginTop: 20,
    width: '100%',
  },
  fileName: {
    fontSize: 16,
    color: '#333',
  },
  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 20,
    fontSize: 16,
    color: '#333',
    textAlign: 'center',
  },
  progressContainer: {
    width: '100%',
    marginVertical: 20,
    alignItems: 'center',
  },
  progressBarBackground: {
    width: '80%',
    height: 10,
    backgroundColor: '#E0E0E0',
    borderRadius: 5,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#007AFF',
  },
  progressText: {
    marginTop: 8,
    fontSize: 16,
    fontWeight: 'bold',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  subtitle: {
    fontSize: 16,
    marginBottom: 32,
    color: '#666',
  },
  uploadArea: {
    borderWidth: 2,
    borderColor: '#007AFF',
    borderStyle: 'dashed',
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F0F8FF',
    marginVertical: 20,
    height: 240,
  },
  supportedFormatsText: {
    fontSize: 14,
    marginTop: 8,
    color: '#888',
    textAlign: 'center',
  },
  changeButton: {
    backgroundColor: '#E1F5FE',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  changeButtonText: {
    color: '#007AFF',
    fontWeight: '500',
  },
  continueButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 8,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 18,
    marginRight: 8,
  },
  documentTypeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  documentTypeLabel: {
    fontSize: 16,
    color: '#333',
    marginRight: 10,
  },
  documentTypeButtons: {
    flexDirection: 'row',
  },
  documentTypeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#007AFF',
    marginRight: 10,
  },
  documentTypeSelected: {
    backgroundColor: '#007AFF',
  },
  documentTypeText: {
    marginLeft: 5,
    color: '#007AFF',
  },
  documentTypeTextSelected: {
    color: '#fff',
  },
  // Add these new styles for the modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    width: '100%',
    maxWidth: 400,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
    textAlign: 'center',
  },
  modalSubtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 20,
    textAlign: 'center',
  },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#F5F7FA',
    borderRadius: 8,
    marginBottom: 12,
  },
  modalOptionTextContainer: {
    flex: 1,
    marginLeft: 12,
    marginRight: 8,
  },
  modalOptionTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  modalOptionDescription: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  modalCancelButton: {
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  modalCancelText: {
    color: '#666',
    fontSize: 16,
    fontWeight: '500',
  },
});

export default FileUploadScreen;