import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const HomeScreen = ({ navigation }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>MCQ Generator</Text>
      <Text style={styles.subtitle}>Choose your input method</Text>

      <TouchableOpacity 
        style={styles.optionCard}
        onPress={() => navigation.navigate('FileUpload')}
      >
        <Ionicons name="document-text" size={32} color="#007AFF" />
        <Text style={styles.optionTitle}>Upload File</Text>
        <Text style={styles.optionDescription}>
          Upload PDF, TXT, or PPT files to generate MCQs
        </Text>
      </TouchableOpacity>

      <TouchableOpacity 
        style={styles.optionCard}
        onPress={() => navigation.navigate('Chat')}
      >
        <Ionicons name="chatbubbles" size={32} color="#007AFF" />
        <Text style={styles.optionTitle}>Enter Text</Text>
        <Text style={styles.optionDescription}>
          Type or paste your content to generate MCQs
        </Text>
      </TouchableOpacity>

      <TouchableOpacity 
        style={styles.optionCard}
        onPress={() => navigation.navigate('MCQGenerator')}
      >
        <Ionicons name="list" size={32} color="#007AFF" />
        <Text style={styles.optionTitle}>Sample MCQs</Text>
        <Text style={styles.optionDescription}>
          Try sample MCQs while API is in development
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
    marginVertical: 20,
    color: '#333',
  },
  subtitle: {
    fontSize: 18,
    textAlign: 'center',
    color: '#666',
    marginBottom: 30,
  },
  optionCard: {
    backgroundColor: '#fff',
    borderRadius: 15,
    padding: 20,
    marginBottom: 15,
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  optionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginVertical: 10,
    color: '#333',
  },
  optionDescription: {
    textAlign: 'center',
    color: '#666',
  },
});

export default HomeScreen;