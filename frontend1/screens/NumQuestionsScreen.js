import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ActivityIndicator, 
  Alert 
} from 'react-native';
import Slider from '@react-native-community/slider';
import { Ionicons } from '@expo/vector-icons';
import { generateMCQsFromAPI, getBaseUrl, generateMCQsFromFileAPI } from '../services/apiService';

const NumQuestionsScreen = ({ navigation, route }) => {
  const [numQuestions, setNumQuestions] = useState(3);
  const [loading, setLoading] = useState(false);
  
  // Extract parameters from the route
  const { contentType, content, fileUri, fileName, fileType, documentType } = route.params || {};

  // Ensure there's content to work with
  if (!content && !fileUri) {
    Alert.alert('Error', 'No content provided for MCQ generation', 
      [{ text: 'Go Back', onPress: () => navigation.goBack() }]
    );
  }

  const handleGenerateMCQs = async () => {
    setLoading(true);
    try {
      let mcqs;
      
      // Check if we're processing a file or direct text content
      if (fileUri && fileName && fileType) {
        // Processing a file
        console.log(`Generating MCQs from file: ${fileName}, type: ${fileType}, document type: ${documentType}`);
        mcqs = await generateMCQsFromFileAPI(fileUri, fileName, fileType, numQuestions);
      } else {
        // Processing direct text content
        console.log(`Attempting to connect to API at: ${getBaseUrl()}/generate-mcqs`);
        console.log('With payload:', { text: content.substring(0, 50) + '...', num_questions: numQuestions });
        mcqs = await generateMCQsFromAPI(content, numQuestions);
      }
      
      console.log('Received MCQs:', mcqs);
      
      if (!mcqs || mcqs.length === 0) {
        throw new Error('No MCQs were generated. Try with different text.');
      }
      
      navigation.navigate('MCQScreen', { mcqs });
    } catch (error) {
      console.error('Detailed error:', error);
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.contentContainer}>
        <Text style={styles.title}>How many questions?</Text>
        
        <View style={styles.sliderContainer}>
          <Text style={styles.sliderLabel}>Number of questions: {numQuestions}</Text>
          <Slider
            style={styles.slider}
            value={numQuestions}
            onValueChange={(value) => setNumQuestions(Math.round(value))}
            minimumValue={1}
            maximumValue={15}
            step={1}
            minimumTrackTintColor="#007AFF"
            maximumTrackTintColor="#DDDDDD"
            thumbTintColor="#007AFF"
          />
          <View style={styles.sliderLimits}>
            <Text style={styles.sliderLimitText}>1</Text>
            <Text style={styles.sliderLimitText}>15</Text>
          </View>
        </View>
        
        <View style={styles.infoContainer}>
          <Ionicons name="information-circle-outline" size={20} color="#007AFF" />
          <Text style={styles.infoText}>
            Generating more questions may take longer. For optimal results, choose between 5-10 questions.
          </Text>
        </View>
      </View>
      
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={() => navigation.goBack()}
        >
          <Ionicons name="arrow-back" size={20} color="#007AFF" />
          <Text style={styles.backButtonText}>Back</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.generateButton}
          onPress={handleGenerateMCQs}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Text style={styles.generateButtonText}>Generate</Text>
              <Ionicons name="create-outline" size={20} color="#fff" />
            </>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    justifyContent: 'space-between',
  },
  contentContainer: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 30,
    textAlign: 'center',
  },
  sliderContainer: {
    marginBottom: 30,
  },
  sliderLabel: {
    fontSize: 18,
    marginBottom: 15,
    textAlign: 'center',
  },
  slider: {
    width: '100%',
    height: 40,
  },
  sliderLimits: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
  },
  sliderLimitText: {
    color: '#888',
  },
  infoContainer: {
    flexDirection: 'row',
    backgroundColor: '#e3f2fd',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  infoText: {
    marginLeft: 10,
    color: '#0069c0',
    flex: 1,
  },
  buttonContainer: {
    flexDirection: 'row',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    marginRight: 10,
  },
  backButtonText: {
    color: '#007AFF',
    marginLeft: 5,
    fontSize: 16,
  },
  generateButton: {
    backgroundColor: '#007AFF',
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 15,
    borderRadius: 8,
  },
  generateButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginRight: 5,
  },
});

export default NumQuestionsScreen;