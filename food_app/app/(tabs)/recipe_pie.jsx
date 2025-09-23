import React, { useState, useEffect } from 'react';
import { PieChart } from 'react-native-chart-kit';
import { Picker } from '@react-native-picker/picker'
import { View, Text, TextInput, Button, StyleSheet, ScrollView } from 'react-native';


const unitmap = {
        // Ounce-based
        'ounce': 2,
        'ounces': 2,
        'oz': 2,
        'onze': 2,  // likely a typo of "ounce"

        // Pound
        'pound': 32,
        'lb': 32,
        'lbs': 32,

        // Cup
        'cup': 16,
        'cups': 16,
        'c': 16,

        //Tablespoon (base unit)
        'tablespoon': 1,
        'tablespoons': 1,
        'tbsp': 1,
        'tbsps': 1,

        // Teaspoon
        'teaspoon': 1 / 3,
        'teaspoons': 1 / 3,
        'tsp': 1 / 3,
        'tsps': 1 / 3,

        // Fluid ounce (1 fl oz ≈ 2 tbsp)
        'fluid ounce': 2,
        'fluid ounces': 2,
        'fl oz': 2,

        // Pint (1 pt = 32 tbsp)
        'pint': 32,
        'pt': 32,

        // Quart (1 qt = 64 tbsp)
        'quart': 64,
        'qt': 64,

        // Gallon (1 gal = 256 tbsp)
        'gallon': 256,
        'gal': 256,

        // Metric (approximate to tbsp) # 이거는 되도록 제외하기
        'milliliter': 1 / 15,
        'milliliters': 1 / 15,
        'ml': 1 / 15,

        'liter': 1000 / 15,
        'liters': 1000 / 15,
        'l': 1000 / 15, // 이거는 조심하기 l가 알파벳 하나라 좀 오류 작동할 수 있을듯
    }

const styles = StyleSheet.create({
    container: { flex: 1, alignItems: 'center', padding: 24 },
    title: { fontSize: 22, marginBottom: 10, fontWeight: 'bold' },
    input: {
        borderWidth: 1, borderColor: '#ccc', borderRadius: 8,
        width: 300, padding: 10, marginBottom: 12,
        fontSize: 16
    },
    loading: { marginTop: 15, fontSize: 16, color: '#888' }
});
export default function App() {

    const [useTextInput, setUseTextInput] = useState(false);
    const [textInput, setTextInput] = useState('');

    const [useEC2, setUseEC2] = useState(true);
    const BASE_URL = useEC2 ? 'http://3.149.161.11:5050' : 'http://localhost:5050';

    const [url, setUrl] = useState('');

    const [groupData, setGroupData] = useState([]); //이런거 쓰는 이유는 전역 변수로 쓰기 위함임
    const [loading, setLoading] = useState(false);
    const [title, setTitle] = useState('');
    const [rawIngredients, setRawIngredients] = useState([]);

    const [selectedIngredient, setSelectedIngredient] = useState(null);
    const [newAmount, setNewAmount] = useState('');
    const [adjustedMap, setAdjustedMap] = useState({});

    const [predictions, setPredictions] = useState([]);

    const fetchIngredients = async () => {
        if(useTextInput && !textInput.trim()) return; // 텍스트 활성화되어도 텍스트가 없으면 return(실행 안됌)
        if (!useTextInput && !url.trim()) return; // url 활성화되어도 url가 없으면 return(실행 안됌)
        setLoading(true);
        try {
            let json; //
            if (useTextInput) {
                const res = await fetch(`${BASE_URL}/parse-text`,{
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ text:textInput})
                });
                json = await res.json(); // 이게 있어야 받아온 값을 저장함
            } else{
                const res = await fetch(`${BASE_URL}/get-ingredients?url=${encodeURIComponent(url)}`);
                json = await res.json();
            }
            

            if (json.error) { // if error happens in server, catch that first
                alert(json.error);  //  서버에서 지원되지 않는 URL일 때 알림
                setGroupData([]);
                setRawIngredients([]);
                return;
            }
            setTitle(json.title); // okay
            setGroupData(json.groupsData.map(group => {
                const total = group.chartData.reduce((sum, item) => sum + item.value, 0) || 1;
                const sortedChartData = [...group.chartData].sort((a, b) => b.value - a.value);
                const chartWithPercent = sortedChartData.map(item => ({
                    ...item,
                    percent: ((item.value) / total * 100).toFixed(2)
                }));
                return {
                    purpose: group.purpose,
                    chartData: chartWithPercent,
                    exceptData: group.exceptData,

                };

            }));
            setRawIngredients(json.raw_ingredients); //  이 줄 추가
            setAdjustedMap({});
        } catch (e) { // if error happens while trying that(not server) we catch that
            alert(e.message);
            console.log(e);
            setGroupData([]);
            setRawIngredients([]); // 에러시도 비워주기

        } finally {
            setLoading(false); //  runs whatever happens
        }
    } // 문제가 저기 있는 value는 tablespoon 기준이고, cup일때는 4 cup / original quantity * 16 이라 무조건 4분의 1이됌
    const adjustIngredients = () => {
        if (!selectedIngredient || !newAmount) return;
        const ratio = (parseFloat(newAmount)* (unitmap[selectedIngredient.unit] || 0))/ selectedIngredient.value;
        const newMap = {};
        groupData.forEach(group => {
            group.chartData.forEach(item => {
                const quantity = (item.quantity * ratio) ;
                newMap[item.raw] = {
                    quantity: quantity.toFixed(2),
                    unit: item.unit,
                    name: item.name
                };
            });
        });
        setAdjustedMap(newMap)
    };

    const fetchPredictions = async () => {
    try {
        const exceptDataAll = groupData.flatMap(g => g.exceptData);
        if (exceptDataAll.length === 0) {
            alert("No except data to predict");
            return;
        }
        const res = await fetch(`${BASE_URL}/predict-grams`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ exceptData: exceptDataAll })
        });
        const json = await res.json();
        if (json.error) {
            alert(json.error);
            return;
        }
        setPredictions(json.predicted);
    } catch (e) {
        alert(e.message);
        console.log(e);
    }
    };

    const makescroll = () => {
        return groupData.map((group, index) => {
            if (loading) return null;

            const hasChartData = group.chartData.length > 0
            const hasExceptData = group.exceptData.length > 0
            return ( //  여기서 원래 return이 나와야 되고, 그 return이 나와야되는 이유는 저 map이 돌아가면서 각각 return할게 있어야되기 때문
                <View key={index} style={{ marginRight: 20 }}>
                    {hasChartData && (
                        <>
                            <PieChart
                                data={group.chartData}
                                width={300}
                                height={200}
                                chartConfig={{
                                    backgroundColor: "#fff",
                                    backgroundGradientFrom: "#fff",
                                    backgroundGradientTo: "#fff",
                                    decimalPlaces: 2,
                                    color: (opacity = 1) => `rgba(50,100,150,${opacity})`,
                                }}
                                accessor="value"
                                backgroundColor="transparent"
                                paddingLeft="15"
                                hasLegend={false}
                            />
                            {/* ChartData - PieChart 밑으로 이동, 내림차순 정렬 */}
                            <View style={{ marginTop: 10, width: 300 }}>
                                <Text style={{ fontWeight: 'bold', fontSize: 16, marginBottom: 3 }}>{group.purpose}</Text>
                                {group.chartData.map((item, idx) => (
                                    <View key={idx} style={{ flexDirection: 'row', alignItems: 'center', marginVertical: 2 }}>
                                        <View style={{
                                            width: 16, height: 16, backgroundColor: item.color,
                                            borderRadius: 8, marginRight: 7, marginTop: 2
                                        }} />
                                        <Text style={{
                                            fontSize: 15,
                                            flexShrink: 1,
                                            flexWrap: 'wrap',
                                            marginRight: 6
                                        }}>
                                            {`${item.percent}% ${item.name}`}
                                        </Text>
                                    </View>
                                ))}
                            </View>
                        </>
                    )}
                    {/* Except Data */}
                    {hasExceptData && (
                        <View style={{ marginTop: 24, alignItems: 'flex-start', width: 300 }}>
                            {group.exceptData.length > 0 && (
                                <>
                                    <Text style={{ fontWeight: 'bold', fontSize: 16 }}>Except Data</Text>
                                    {group.exceptData.map((item, idx) => (
                                        <Text key={idx} style={{ fontSize: 15, marginVertical: 2 }}>
                                            {item.quantity ? item.quantity + ' ' : ''}
                                            {item.unit ? item.unit + ' ' : ''}
                                            {item.name}
                                        </Text>
                                    ))}
                                </>
                            )}
                        </View>
                    )}
                </View>
            );
        });
    };
    return (
        <ScrollView contentContainerStyle={[styles.container, {flexGrow:1}]}>
            {/* Title */}
            <Text style={styles.title}>Ingredients Pie chart</Text>
            <Button
                title = {useTextInput ? "Switch to URL Mode" : "Switch to Text Mode"}
                onPress = {() => setUseTextInput(prev => !prev)}
                color = "#444"
                style= {{marginBottom:10}}
            />
            <Text>{useTextInput ? "Paste Ingredient Text" : "Put Recipe URL" }</Text>
            {useTextInput ? (
                <TextInput
                style={[styles.input, {height: 120, textAlignVertical:'top', flexShrink: 0}]}
                value={textInput}
                onChangeText={setTextInput}
                multiline = {true}
                placeholder={`e.g.\n2 cups flour\n1 tbsp sugar\n...`}
                autoCapitalize="none"
                autoCorrect={false}
                />
            ): (
                <TextInput
                style={styles.input}
                value={url}
                onChangeText={setUrl}
                placeholder="https://example.com/recipe"
                autoCapitalize="none"
                autoCorrect={false}
                />
            )}
            
            <Button title="Convert to Chart" onPress={fetchIngredients} disabled={loading} />
            {loading && <Text style={styles.loading}> Loading...</Text>}
            <Button title={useEC2 ? "Using EC2 (tap to switch to Local)" : "Using Localhost (tap to switch to EC2)"}
                onPress={() => setUseEC2(prev => !prev)}
                color="#666"
                style={{ marginTop: 8 }}>
            </Button>
            {/* Piechart + ChartData (legend) */}
            {!loading && groupData.length > 0 && (
                <>
                    {/* multiple <></>가 있다면 text or {} 그리고 그게 View 같은걸로 감싸져있지 않으면 <></>로 감싸줘야함 */}
                    <Text style={{ fontSize: 18, fontWeight: 'bold', marginVertical: 12 }}>{title}</Text>
                    {/* # TODO 
                    Sugar 밑에 있는거 선택해도 위에있는게 선택되고 tablespoon 이 아니라 cup이 나옴,
                    raw를 고유값으로 한다 했는데, 그거 말고 idx 생각하기 왜냐하면 group이 달라지면 같은 값의 raw가 나올 수 도 있기 때문*/}
                    {makescroll()}
                    {/* Adjust ingredient field */}
                    <View style={{ marginVertical: 20, width: 300 }}>
                        <Text style={{ fontWeight: 'bold', fontSize: 16 }}>Adjust Ingredient</Text>
                        <Picker
                            selectedValue={selectedIngredient?.raw || ''}
                            style={{ height: 30, width: '100%' }}
                            onValueChange={(itemRaw) => {
                                const found = groupData.flatMap(g => g.chartData).find(item => item.raw === itemRaw)
                                setSelectedIngredient(found);
                            }}>
                            <Picker.Item label="Pick an Ingredient" value="" />
                            {rawIngredients.map((line,idx)=> {
                                const item = groupData.flatMap(g => g.chartData).find(i => line.includes(i.raw)); // 이것도 조정해야됐었다
                                if (!item) return null;
                                return <Picker.Item key={idx} label={item.name} value={item.raw} />;// 저 value를 통해서 구별하는데 name은 겹쳐서 같은 것으로 인식하니 raw로 하자 아예 다르니까
                            })}
                        </Picker>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                            <TextInput
                                style={[styles.input, { flex: 1, marginRight: 10, fontSize: 16 }]}
                                value={newAmount}
                                onChangeText={(text) => {
                                    const cleaned = text.replace(/[^0-9.]/g, '');
                                    const parts = cleaned.split('.');
                                    if (parts.length > 2) {
                                        setNewAmount(parts[0] + '.' + parts.slice(1).join(''));
                                    } else {
                                        setNewAmount(cleaned);
                                    }
                                }}

                                placeholder="Enter new amount"
                                keyboardType="numeric" // only numbers
                            />
                            <Text style={{ fontSize: 16 }}> {selectedIngredient?.unit || ''}</Text>
                        </View>

                        <Button title="Apply Adjustments" onPress={adjustIngredients} />
                        <View style={{ height: 8 }} />
                        <Button
                            title="Reset"
                            onPress={() => {
                                setSelectedIngredient(null);
                                setNewAmount('');
                                setAdjustedMap({});
                            }}
                            color="#888"

                        />
                    </View>
                    <Button 
                        title="Predict Grams for Except Data"
                        onPress={fetchPredictions}
                        color="#444"
                        style={{ marginTop: 12 }}
                    />

                    {predictions.length > 0 && (
                        <View style={{ marginTop: 20, width: 300 }}>
                            <Text style={{ fontWeight: 'bold', fontSize: 16 }}>Predicted Grams</Text>
                            {predictions.map((item, idx) => (
                            <Text key={idx} style={{ fontSize: 15, marginVertical: 2 }}>
                                {item.raw} → {item.total_prediction} g  ({item.quantity} × {item.base_prediction} g)
                            </Text>
                            ))}
                        </View>
                    )}
                    {rawIngredients.length > 0 && (
                        <View style={{ flexDirection: 'column', alignItems: 'flex-start', marginTop: 20 }}>
                            <Text style={{ fontWeight: 'bold', fontSize: 15, marginTop: 12 }}>Raw Ingredients</Text>
                            {rawIngredients.map((line, idx) => {
                                const adjusted = adjustedMap[line]; // 괄호 → 대괄호로 수정
                                return (
                                    <View key={idx} style={{ flexDirection: 'row', justifyContent: adjusted ? 'space-between' : 'flex-start', marginBottom: 4, width: '100%' }}>
                                        <Text style={{ fontSize: 14, flex: 1 }}>{line}</Text>
                                        {adjusted && (

                                            <Text style={{ fontSize: 14, flex: 1, textAlign: 'right' }}> →
                                                {adjusted.quantity} {adjusted.unit} {adjusted.name}
                                            </Text>

                                        )}
                                    </View>
                                );
                            })}
                        </View>
                    )}

                </>

            )}
        </ScrollView>

    );

}