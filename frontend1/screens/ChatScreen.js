import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator, Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { generateMCQsFromAPI } from '../services/apiService';

const ChatScreen = ({ navigation }) => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const validateInput = () => {
    if (!text.trim()) {
      setErrorMessage('Please enter some text to generate questions from');
      return false;
    }
    
    if (text.trim().length < 50) {
      setErrorMessage('Please enter at least 50 characters for better results');
      return false;
    }
    
    return true;
  };

  const handleContinue = async () => {
    if (!validateInput()) return;
    
    // Instead of generating MCQs directly, navigate to the NumQuestionsScreen
    navigation.navigate('NumQuestions', {
      contentType: 'text',
      content: text
    });
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Text style={styles.title}>Enter Text for MCQ Generation</Text>
        <Text style={styles.description}>
          Enter or paste text from which you want to generate multiple-choice questions.
        </Text>
        
        <TextInput
          style={styles.textInput}
          multiline
          numberOfLines={10}
          placeholder="Paste your text here (minimum 50 characters)..."
          value={text}
          onChangeText={(value) => {
            setText(value);
            setErrorMessage('');
          }}
        />
        
        {errorMessage ? (
          <Text style={styles.errorText}>{errorMessage}</Text>
        ) : null}
        
        <TouchableOpacity
          style={[styles.button, loading && styles.disabledButton]}
          onPress={handleContinue}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Text style={styles.buttonText}>Generate MCQs</Text>
              <Ionicons name="arrow-forward" size={20} color="#fff" />
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContainer: {
    padding: 16,
    flexGrow: 1,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  description: {
    fontSize: 16,
    color: '#666',
    marginBottom: 24,
  },
  textInput: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    minHeight: 200,
    textAlignVertical: 'top',
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  errorText: {
    color: 'red',
    marginTop: 8,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 8,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 24,
  },
  disabledButton: {
    backgroundColor: '#8CC5FF',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 18,
    marginRight: 8,
  },
});

export default ChatScreen;