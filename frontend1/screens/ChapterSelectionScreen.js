import React, { useState } from 'react';
import { 
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const ChapterSelectionScreen = ({ route, navigation }) => {
  const { chapters, fileName } = route.params || { chapters: [] };
  const [selectedChapters, setSelectedChapters] = useState([]);
  
  const toggleChapterSelection = (index) => {
    if (selectedChapters.includes(index)) {
      setSelectedChapters(selectedChapters.filter(i => i !== index));
    } else {
      setSelectedChapters([...selectedChapters, index]);
    }
  };
  
  const handleContinue = () => {
    if (selectedChapters.length === 0) {
      Alert.alert('Error', 'Please select at least one chapter');
      return;
    }
    
    // Combine selected chapters' content
    const selectedContent = selectedChapters
      .map(index => chapters[index].content)
      .join('\n\n');
    
    // Go to the number of questions screen
    navigation.navigate('NumQuestions', { text: selectedContent });
  };
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Select Chapters</Text>
      <Text style={styles.subtitle}>{fileName}</Text>
      
      <FlatList
        data={chapters}
        keyExtractor={(_, index) => `chapter-${index}`}
        renderItem={({ item, index }) => (
          <TouchableOpacity
            style={[
              styles.chapterItem,
              selectedChapters.includes(index) && styles.selectedChapter
            ]}
            onPress={() => toggleChapterSelection(index)}
          >
            <View style={styles.chapterContent}>
              <Text style={styles.chapterTitle}>{item.title}</Text>
              <Text style={styles.chapterPreview}>
                {item.content.substring(0, 50)}...
              </Text>
            </View>
            <View style={styles.checkbox}>
              {selectedChapters.includes(index) ? (
                <Ionicons name="checkmark-circle" size={24} color="#007AFF" />
              ) : (
                <Ionicons name="ellipse-outline" size={24} color="#999" />
              )}
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>No chapters detected</Text>
          </View>
        }
      />
      
      <View style={styles.buttonContainer}>
        <TouchableOpacity
          style={[
            styles.continueButton,
            selectedChapters.length === 0 && styles.disabledButton
          ]}
          onPress={handleContinue}
          disabled={selectedChapters.length === 0}
        >
          <Text style={styles.buttonText}>Continue</Text>
          <Ionicons name="arrow-forward" size={24} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 20,
  },
  chapterItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    marginBottom: 12,
  },
  selectedChapter: {
    backgroundColor: '#e3f2fd',
    borderColor: '#007AFF',
    borderWidth: 1,
  },
  chapterContent: {
    flex: 1,
  },
  chapterTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  chapterPreview: {
    fontSize: 14,
    color: '#666',
  },
  checkbox: {
    marginLeft: 10,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  emptyText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
  buttonContainer: {
    marginTop: 16,
  },
  continueButton: {
    backgroundColor: '#007AFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginRight: 8,
  },
});

export default ChapterSelectionScreen;