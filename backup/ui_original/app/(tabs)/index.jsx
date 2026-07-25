import blackcoffee from "@/assets/images/black-coffee.jpg"
import { Link } from 'expo-router'
import React from 'react'
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native'


const index = () => {
  const [count, setCount] = React.useState(0);
  const topics = [
    { id: 1, title: 'Coffee', describe :"Coffee is good"},
    { id: 2, title: 'Tea', describe :"Tea is good"},
  ]
  return (

    <View style = {styles.container}>
      <ImageBackground source = {blackcoffee} style = {styles.image}  >
      <Text style = {styles.title}>Black Coffee</Text>
      <Link href='/button' style ={{marginHorizontal:'auto'}} asChild>
      {/* marginHorizontal:'auto' 텍스트만큼의 크기로 이것을 변경해준다*/}
        <Pressable style = {styles.Button}>
          <Text style = {styles.ButtonText}> Button</Text>
        </Pressable>
      </Link>
      <Link href='/food_main' style ={{marginHorizontal:'auto'}} asChild>
      {/* marginHorizontal:'auto' 텍스트만큼의 크기로 이것을 변경해준다*/}
        <Pressable style = {styles.Button}>
          <Text style = {styles.ButtonText}> Food Main</Text>
        </Pressable>
      </Link>
      {/* <Button title = "Increase" onPress={()=> setCount(count+1)}/>  */}
            <Link href='/recipe_pie' style ={{marginHorizontal:'auto'}} asChild>
      {/* marginHorizontal:'auto' 텍스트만큼의 크기로 이것을 변경해준다*/}
        <Pressable style = {styles.Button}>
          <Text style = {styles.ButtonText}> Recipe Pie Chart</Text>
        </Pressable>
      </Link>
      </ImageBackground>
      </View>
      
      
  )

}

export default index

const styles = StyleSheet.create({
  container: {
    flex: 10,
    flexDirection: 'column'
  },
  image:{
    flex:1,
    justifyContent: 'center',
    width: '100%',
    height: '100%',
    resizeMode: 'cover'
  },
  title:{
    color :'white',
    fontSize:42,
    fontWeight:'bold',
    textAlign: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    marginBottom: 120

  },
  link:{
    color :'white',
    fontSize:42,
    fontWeight:'bold',
    textAlign: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    textDecorationLine: 'underline',
    padding:4,
  },
  Button:{
    width: 100,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.5)',
    padding:6,
    justifyContent: 'center',
    margin: 5

  },
  ButtonText:{
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  }

})