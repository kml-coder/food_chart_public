import React, { useState } from 'react';
import { Button, FlatList, ScrollView, StyleSheet, Text, View } from 'react-native';

export default function FoodMain() {
    type Recipe ={
        id: string;
        name: string;
        likes: number;
    }
    const [recipes, setRecipes] = useState<Recipe[]>([
        { id: '1', name: "Lakshmi's Brownie", likes: 0},
        { id: '2', name: "Brenna's Brownie", likes: 0},
        { id: '3', name: "Jason's Milk", likes: 0},
        { id: '4', name: "Kyungmin's Chicken", likes: 0},
    ]);
    const handleLike = (id: string) => {
        const updated = recipes.map( item =>
            item.id === id ? {...item, likes: item.likes+1} : item);
        setRecipes(updated);
    };
    const renderItem = ({ item }: { item: Recipe }) => (
        <View style = {styles.item}>
            <Text style ={styles.name}> {item.name}</Text>
            <Text> Likes: {item.likes}</Text>
            <Button title="Like" onPress={() => handleLike(item.id)}></Button>
        </View>

    );
    return (
        <ScrollView style={styles.container}>
            <Text style = {styles.title}> Brownies' Ranking</Text>
            <FlatList
                data = {recipes}
                renderItem = {renderItem}
                keyExtractor = {item => item.id}
                />
            <Button title = "Reset" onPress={() => {setRecipes(recipes.map(item=>( {...item, likes: 0}))); setTimeout( () => { alert("Likes reset!") }, 1000)}}/> 
                {/* 그냥 함수 쓰면 바로 실행되니까, 변수처럼 전달 가능한 형태인 임시함수로 만들고, 0을 붙여서 setTimeout에 전달해준다 */}
        </ScrollView>
    );
}
const styles = StyleSheet.create({
        container: {
    marginTop: 60,
    padding: 20
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20

  },
  item: {
    backgroundColor: '#eee',
    padding: 20,
    marginBottom: 10,
    borderRadius: 8
  },
  name: {
    fontSize: 18,
    marginBottom: 5,
    textAlign: 'center'
  }
});