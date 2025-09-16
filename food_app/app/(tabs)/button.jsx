import {Button, View, Text} from 'react-native'
import React from 'react'
import {Link} from 'expo-router'

const ButtonComponent = () => {
    const [count, SetCount] = React.useState(0);
    return (
        <View>
            <Link href ='/' style = {{borderRadius: 10,marginHorizontal:'auto',fontSize:42,color:'white',textAlign:'center',padding: 4,backgroundColor:'rgba(0,0,0,0.5)'}}>Index</Link>
            <Text>Count: {count}</Text>
            <Button title="Increase" onPress={() => SetCount(count+1)}/>
            <Button title="Decrease" onPress={() => SetCount(count-1)}/>
        </View>
    )
}
export default ButtonComponent
