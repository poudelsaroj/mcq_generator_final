import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { generateMCQFile } from '../utils/pdfGenerator';

const MCQScreen = ({ route, navigation }) => {
  const { mcqs } = route.params;
  const [showMCQs, setShowMCQs] = useState(false);

  if (!mcqs || mcqs.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>No MCQs were generated. Please try again with different text.</Text>
        <TouchableOpacity
          style={styles.button}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.buttonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Handle download action with format selection
  const handleDownload = () => {
    Alert.alert(
      'Download MCQs',
      'Choose a format to download',
      [
        {
          text: 'PDF',
          onPress: () => generateMCQFile(formatMCQsForDownload(mcqs), 'pdf')
        },
        {
          text: 'Text File',
          onPress: () => generateMCQFile(formatMCQsForDownload(mcqs), 'txt')
        },
        {
          text: 'Cancel',
          style: 'cancel'
        }
      ]
    );
  };

  // Format MCQs to match the format expected by pdfGenerator
  const formatMCQsForDownload = (mcqs) => {
    return mcqs.map(mcq => ({
      question: mcq.question,
      answer: mcq.correct_answer,
      distractors: mcq.options.filter(option => option !== mcq.correct_answer)
    }));
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.summaryCard}>
        <Text style={styles.title}>MCQs Generated</Text>
        <Text style={styles.summaryText}>
          {mcqs.length} multiple-choice questions have been successfully generated.
        </Text>
        <Text style={styles.instructionText}>
          You can take an assessment with these questions or download them in your preferred format.
        </Text>
      </View>
      
      <TouchableOpacity 
        style={styles.toggleButton}
        onPress={() => setShowMCQs(!showMCQs)}
      >
        <Text style={styles.toggleButtonText}>
          {showMCQs ? 'Hide MCQs' : 'Preview MCQs'}
        </Text>
        <Ionicons name={showMCQs ? "eye-off-outline" : "eye-outline"} size={20} color="#007AFF" />
      </TouchableOpacity>
      
      {/* Only show MCQs if toggle is enabled */}
      {showMCQs && mcqs.map((mcq, index) => (
        <View key={index} style={styles.mcqContainer}>
          <Text style={styles.questionNumber}>Question {index + 1}</Text>
          <Text style={styles.question}>{mcq.question}</Text>
          
          {mcq.options.map((option, optionIndex) => (
            <View key={optionIndex} style={styles.optionContainer}>
              <View style={[
                styles.optionIndicator, 
                option === mcq.correct_answer ? styles.correctIndicator : {}
              ]}>
                <Text style={styles.optionLetter}>{String.fromCharCode(65 + optionIndex)}</Text>
              </View>
              <Text style={styles.optionText}>{option}</Text>
            </View>
          ))}
          
          <View style={styles.answerContainer}>
            <Text style={styles.answerLabel}>Correct Answer:</Text>
            <Text style={styles.answerText}>{mcq.correct_answer}</Text>
          </View>
        </View>
      ))}
      
      {/* Action buttons */}
      <View style={styles.actionContainer}>
        <TouchableOpacity
          style={[styles.actionButton, styles.assessButton]}
          onPress={() => navigation.navigate('MCQAssessment', { 
            generatedMCQs: formatMCQsForDownload(mcqs)
          })}
        >
          <Ionicons name="school-outline" size={24} color="#fff" />
          <Text style={styles.actionButtonText}>Take Assessment</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.actionButton, styles.downloadButton]}
          onPress={handleDownload}
        >
          <Ionicons name="download-outline" size={24} color="#fff" />
          <Text style={styles.actionButtonText}>Download</Text>
        </TouchableOpacity>
      </View>
      
      <TouchableOpacity
        style={styles.homeButton}
        onPress={() => navigation.navigate('Home')}
      >
        <Text style={styles.buttonText}>Done</Text>
        <Ionicons name="checkmark-circle" size={20} color="#fff" />
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f5f5f5',
  },
  summaryCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  summaryText: {
    fontSize: 18,
    textAlign: 'center',
    color: '#4CAF50',
    fontWeight: 'bold',
    marginBottom: 8,
  },
  instructionText: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginTop: 8,
  },
  toggleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    marginVertical: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  toggleButtonText: {
    color: '#007AFF',
    fontWeight: '600',
    fontSize: 16,
    marginRight: 8,
  },
  mcqContainer: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
  // Keep all existing styles below this line
  questionNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 8,
  },
  question: {
    fontSize: 18,
    marginBottom: 16,
    lineHeight: 24,
  },
  optionContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  optionIndicator: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#e0e0e0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  correctIndicator: {
    backgroundColor: '#4CAF50',
  },
  optionLetter: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  optionText: {
    fontSize: 16,
    flex: 1,
  },
  answerContainer: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#f0f8ff',
    borderRadius: 6,
  },
  answerLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 4,
  },
  answerText: {
    fontSize: 16,
    fontWeight: '500',
  },
  actionContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 20,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    flex: 1,
  },
  assessButton: {
    backgroundColor: '#4CAF50',
    marginRight: 8,
  },
  downloadButton: {
    backgroundColor: '#FF9800',
    marginLeft: 8,
  },
  actionButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
    marginLeft: 8,
  },
  homeButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 8,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 18,
    marginRight: 8,
  },
  errorText: {
    fontSize: 16,
    color: 'red',
    textAlign: 'center',
    marginBottom: 20,
  },
});

export default MCQScreen;