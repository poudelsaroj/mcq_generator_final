import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { generateMCQs, generateDistractors } from '../services/mcqService';
// import MCQCard from '../components/MCQCard';

export default function MCQGeneratorScreen() {
  const [text, setText] = useState('');
  const [mcqs, setMcqs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');

  const handleGenerateMCQs = async () => {
    if (!text.trim()) {
      setError('Please enter some text');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const questions = await generateMCQs(text, 4); // Default to 4 questions
      setMcqs(questions);
    } catch (error) {
      setError(error.message || 'Failed to generate MCQs');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDistractors = async () => {
    if (!answer.trim()) {
      Alert.alert('Error', 'Please enter an answer first');
      return;
    }

    setLoading(true);
    try {
      const distractors = await generateDistractors(answer);
      console.log('Generated distractors:', distractors);
      // Handle the distractors here - e.g. update state, display them, etc.
      
    } catch (error) {
      Alert.alert('Error', 'Failed to generate distractors');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>MCQ Generator</Text>
      <TextInput
        style={styles.input}
        placeholder="Enter text to generate MCQs"
        value={text}
        onChangeText={setText}
        multiline
        numberOfLines={6}
      />
      
      <Button title="Generate MCQs" onPress={handleGenerateMCQs} disabled={loading} />
      
      {loading && <ActivityIndicator size="large" color="#0000ff" />}
      
      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : null}
      
      {mcqs.map((item, index) => (
        <View key={index} style={styles.questionCard}>
          <Text style={styles.question}>{item.question}</Text>
          <Text style={styles.answer}>Correct Answer: {item.answer}</Text>
          <Text style={styles.distractorsTitle}>Distractors:</Text>
          {item.distractors.map((distractor, idx) => (
            <Text key={idx} style={styles.distractor}>• {distractor}</Text>
          ))}
        </View>
      ))}

      <TextInput
        value={answer}
        onChangeText={setAnswer}
        placeholder="Enter correct answer"
        style={styles.input}
      />
      <Button 
        title={loading ? "Generating..." : "Generate Distractors"}
        onPress={handleGenerateDistractors}
        disabled={loading}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  input: {
    height: 150,
    borderColor: '#ddd',
    borderWidth: 1,
    marginBottom: 20,
    padding: 10,
    borderRadius: 5,
    backgroundColor: '#fff',
    textAlignVertical: 'top',
  },
  error: {
    color: 'red',
    marginTop: 10,
  },
  questionCard: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginTop: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 3,
  },
  question: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  answer: {
    fontSize: 16,
    color: 'green',
    marginBottom: 10,
  },
  distractorsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 5,
  },
  distractor: {
    fontSize: 16,
    marginLeft: 10,
  },
});