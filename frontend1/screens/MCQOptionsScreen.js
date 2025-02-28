import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Switch, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { generateMCQFile } from '../utils/pdfGenerator';

const MCQOptionsScreen = ({ route, navigation }) => {
  // Pull in the generated MCQs from the route parameters
  const { generatedMCQs = [], numQuestions = 5 } = route.params || {};
  const [showAnswers, setShowAnswers] = useState(false);

  const handleDownload = (format) => {
    Alert.alert(
      'Choose Format',
      'Select the format for downloading MCQs',
      [
        {
          text: 'PDF',
          onPress: () => generateMCQFile(generatedMCQs, 'pdf')
        },
        {
          text: 'Text File',
          onPress: () => generateMCQFile(generatedMCQs, 'txt')
        },
        {
          text: 'Cancel',
          style: 'cancel'
        }
      ]
    );
  };

  if (!generatedMCQs || generatedMCQs.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.noContent}>No MCQs generated yet.</Text>
        <TouchableOpacity 
          style={styles.button} 
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.buttonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Generated MCQs</Text>
        <View style={styles.toggleContainer}>
          <Text>Show Answers</Text>
          <Switch 
            value={showAnswers} 
            onValueChange={setShowAnswers} 
            trackColor={{ false: "#767577", true: "#81b0ff" }}
            thumbColor={showAnswers ? "#007AFF" : "#f4f3f4"}
          />
        </View>
      </View>

      <ScrollView style={styles.scrollView}>
        {generatedMCQs.map((mcq, index) => (
          <View key={index} style={styles.mcqCard}>
            <Text style={styles.questionNumber}>Question {index + 1}</Text>
            <Text style={styles.questionText}>{mcq.question}</Text>
            
            {/* Options: correct answer first, followed by distractors */}
            <View style={styles.optionsList}>
              {[mcq.answer, ...mcq.distractors].map((option, optIndex) => (
                <View key={optIndex} style={styles.optionItem}>
                  <Text style={styles.optionLabel}>
                    {String.fromCharCode(65 + optIndex)}.
                  </Text>
                  <Text 
                    style={[
                      styles.optionText, 
                      showAnswers && option === mcq.answer ? styles.correctOption : null
                    ]}
                  >
                    {option}
                  </Text>
                </View>
              ))}
            </View>

            {showAnswers && (
              <View style={styles.answerContainer}>
                <Text style={styles.answerText}>
                  Correct Answer: {mcq.answer}
                </Text>
              </View>
            )}
          </View>
        ))}
      </ScrollView>

      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={styles.button}
          onPress={() => navigation.navigate('MCQAssessment', { generatedMCQs })}
        >
          <Text style={styles.buttonText}>Start Assessment</Text>
          <Ionicons name="play" size={20} color="#fff" />
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.button}
          onPress={() => handleDownload('pdf')}
        >
          <Text style={styles.buttonText}>Download</Text>
          <Ionicons name="download-outline" size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  toggleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  noContent: {
    textAlign: 'center',
    marginTop: 20,
    fontSize: 16,
    color: '#666',
  },
  mcqCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  questionNumber: {
    fontWeight: 'bold',
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  questionText: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  optionsList: {
    marginLeft: 8,
  },
  optionItem: {
    flexDirection: 'row',
    marginBottom: 8,
    padding: 8,
    backgroundColor: '#f9f9f9',
    borderRadius: 4,
  },
  optionLabel: {
    width: 24,
    fontWeight: '600',
  },
  optionText: {
    flex: 1,
  },
  correctOption: {
    color: 'green',
    fontWeight: '600',
  },
  answerContainer: {
    marginTop: 10,
    padding: 8,
    backgroundColor: '#e8f4e8',
    borderRadius: 4,
  },
  answerText: {
    color: 'green',
    fontWeight: '500',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  button: {
    backgroundColor: '#007AFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 14,
    borderRadius: 8,
    flex: 1,
    marginHorizontal: 8,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginRight: 8,
  },
});

export default MCQOptionsScreen;