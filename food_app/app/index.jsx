import React, { useState, useEffect, useMemo } from 'react';
import { PieChart } from 'react-native-chart-kit';
import { Picker } from '@react-native-picker/picker'
import { View, Text, TextInput, Pressable, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';

const COLORS = {
    bg: '#f6f5f3',
    card: '#ffffff',
    border: '#e4e1dc',
    text: '#1f1d1b',
    muted: '#6f6a64',
    accent: '#e0632c',
    accentSoft: '#fdf0e9',
    // Prefilled sample text: dimmer than real input so it reads as a suggestion.
    sample: '#a7a099',
};

const CONTENT_WIDTH = 620;
const CHART_WIDTH = 300;
// Rendering all ~580 hosts at once is slow in the browser, so the unfiltered
// list is trimmed and the remainder is announced instead of silently dropped.
const SITE_PREVIEW_LIMIT = 120;

const styles = StyleSheet.create({
    screen: { backgroundColor: COLORS.bg },
    container: { alignItems: 'center', paddingVertical: 40, paddingHorizontal: 20 },
    content: { width: '100%', maxWidth: CONTENT_WIDTH },

    title: { fontSize: 30, fontWeight: '700', color: COLORS.text, letterSpacing: -0.5 },
    subtitle: { fontSize: 15, color: COLORS.muted, marginTop: 6, marginBottom: 24, lineHeight: 21 },

    card: {
        backgroundColor: COLORS.card,
        borderWidth: 1,
        borderColor: COLORS.border,
        borderRadius: 14,
        padding: 20,
        marginBottom: 16,
    },
    sectionTitle: { fontSize: 13, fontWeight: '700', color: COLORS.muted, letterSpacing: 0.8, marginBottom: 12 },

    segment: { flexDirection: 'row', backgroundColor: COLORS.bg, borderRadius: 10, padding: 4, marginBottom: 16 },
    segmentItem: { flex: 1, paddingVertical: 8, borderRadius: 7, alignItems: 'center' },
    segmentItemActive: { backgroundColor: COLORS.card, borderWidth: 1, borderColor: COLORS.border },
    segmentLabel: { fontSize: 14, color: COLORS.muted, fontWeight: '600' },
    segmentLabelActive: { color: COLORS.text },

    input: {
        borderWidth: 1,
        borderColor: COLORS.border,
        borderRadius: 10,
        backgroundColor: COLORS.card,
        paddingHorizontal: 14,
        paddingVertical: 12,
        fontSize: 15,
        color: COLORS.text,
        width: '100%',
    },
    inputSample: { color: COLORS.sample },
    textarea: { height: 140, textAlignVertical: 'top' },

    button: {
        backgroundColor: COLORS.accent,
        paddingVertical: 13,
        paddingHorizontal: 20,
        borderRadius: 10,
        alignItems: 'center',
    },
    buttonSecondary: { backgroundColor: COLORS.card, borderWidth: 1, borderColor: COLORS.border },
    buttonDisabled: { opacity: 0.5 },
    buttonLabel: { color: '#fff', fontSize: 15, fontWeight: '600' },
    buttonLabelSecondary: { color: COLORS.text },

    chip: {
        paddingVertical: 7,
        paddingHorizontal: 14,
        borderRadius: 999,
        borderWidth: 1,
        borderColor: COLORS.border,
        backgroundColor: COLORS.card,
        marginRight: 8,
        marginBottom: 8,
    },
    chipActive: { backgroundColor: COLORS.accentSoft, borderColor: COLORS.accent },
    chipLabel: { fontSize: 13, color: COLORS.muted, fontWeight: '600' },
    chipLabelActive: { color: COLORS.accent },

    legendRow: { flexDirection: 'row', alignItems: 'center', marginVertical: 3 },
    legendDot: { width: 12, height: 12, borderRadius: 6, marginRight: 9 },
    legendText: { fontSize: 14, color: COLORS.text, flexShrink: 1 },

    listItem: { fontSize: 14, color: COLORS.text, marginVertical: 3 },
    hint: { fontSize: 13, color: COLORS.muted, lineHeight: 19 },

    siteItem: { fontSize: 12, color: COLORS.muted, width: '33%', paddingVertical: 2 },
});

function ActionButton({ label, onPress, disabled, variant }) {
    const secondary = variant === 'secondary';
    return (
        <Pressable
            onPress={onPress}
            disabled={disabled}
            style={({ pressed }) => [
                styles.button,
                secondary && styles.buttonSecondary,
                disabled && styles.buttonDisabled,
                pressed && !disabled && { opacity: 0.75 },
            ]}>
            <Text style={[styles.buttonLabel, secondary && styles.buttonLabelSecondary]}>{label}</Text>
        </Pressable>
    );
}

const formatGroupForChart = (group) => {
    const sortedChartData = [...group.chartData].sort((a, b) => b.value - a.value);
    const total = sortedChartData.reduce((sum, item) => sum + (Number(item.value) || 0), 0) || 1;
    const chartWithPercent = sortedChartData.map(item => ({
        ...item,
        percent: (((Number(item.value) || 0) / total) * 100).toFixed(2)
    }));
    return {
        ...group,
        chartData: chartWithPercent
    };
};

// Sites the backend's `recipe-scrapers` build can parse. Fetched instead of
// hardcoded so a library upgrade shows up here without a frontend change.
function SupportedSites({ baseUrl }) {
    const [sites, setSites] = useState([]);
    const [error, setError] = useState(null);
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');

    useEffect(() => {
        let cancelled = false;
        fetch(`${baseUrl}/supported-sites`)
            .then((res) => res.json())
            .then((json) => {
                if (cancelled) return;
                if (json.error) setError(json.error);
                else setSites(json.sites || []);
            })
            .catch((e) => { if (!cancelled) setError(e.message); });
        return () => { cancelled = true; };
    }, [baseUrl]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return q ? sites.filter((s) => s.includes(q)) : sites;
    }, [sites, query]);

    if (error) {
        return <Text style={styles.hint}>Supported site list unavailable ({error}).</Text>;
    }
    if (sites.length === 0) {
        return <Text style={styles.hint}>Loading the supported website list…</Text>;
    }

    const shown = query.trim() ? filtered : filtered.slice(0, SITE_PREVIEW_LIMIT);
    const hidden = filtered.length - shown.length;

    return (
        <View>
            <Pressable onPress={() => setOpen((prev) => !prev)}>
                <Text style={[styles.hint, { color: COLORS.accent, fontWeight: '600' }]}>
                    {open ? '▾' : '▸'} {sites.length} supported websites
                </Text>
            </Pressable>
            <Text style={[styles.hint, { marginTop: 4 }]}>
                URL mode uses the recipe-scrapers library, so it only works on sites it has a
                parser for. Anything else — use Text mode and paste the ingredients.
            </Text>

            {open && (
                <View style={{ marginTop: 12 }}>
                    <TextInput
                        style={[styles.input, { fontSize: 13, paddingVertical: 9 }]}
                        value={query}
                        onChangeText={setQuery}
                        placeholder="Filter, e.g. allrecipes"
                        autoCapitalize="none"
                        autoCorrect={false}
                    />
                    <ScrollView style={{ maxHeight: 220, marginTop: 10 }} nestedScrollEnabled>
                        <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                            {shown.map((site) => (
                                <Text key={site} style={styles.siteItem} numberOfLines={1}>{site}</Text>
                            ))}
                        </View>
                        {filtered.length === 0 && (
                            <Text style={styles.hint}>No match for “{query}”.</Text>
                        )}
                        {hidden > 0 && (
                            <Text style={[styles.hint, { marginTop: 8 }]}>
                                +{hidden} more — type above to search the full list.
                            </Text>
                        )}
                    </ScrollView>
                </View>
            )}
        </View>
    );
}

export default function App() {

    const [useTextInput, setUseTextInput] = useState(false);
    const [textInput, setTextInput] = useState('');

    // [LOCAL-ONLY MODE]
    // Keep old EC2 toggle for reference only.
    // const [useEC2, setUseEC2] = useState(false);
    // const BASE_URL = useEC2 ? 'http://3.149.161.11:5050' : 'http://localhost:5050';

    // Empty string = same-origin. In the all-in-one deployment the Flask server
    // also serves this web bundle, so no absolute host is needed.
    // For local dev against a separate backend, set EXPO_PUBLIC_API_URL in food_app/.env.
    const BASE_URL = process.env.EXPO_PUBLIC_API_URL || '';

    // Prefilled so the URL mode is testable with a single tap. Cleared the first
    // time the user focuses the field, so typing a real link replaces the sample.
    const SAMPLE_URL = 'https://sugarspunrun.com/best-cheesecake-recipe/';
    const [url, setUrl] = useState(SAMPLE_URL);
    const [urlTouched, setUrlTouched] = useState(false);

    const [groupData, setGroupData] = useState([]); //이런거 쓰는 이유는 전역 변수로 쓰기 위함임
    const [loading, setLoading] = useState(false);
    const [title, setTitle] = useState('');
    const [rawIngredients, setRawIngredients] = useState([]);

    const [selectedIngredient, setSelectedIngredient] = useState(null);
    const [newAmount, setNewAmount] = useState('');
    const [adjustedMap, setAdjustedMap] = useState({});

    const [predictions, setPredictions] = useState([]);
    const [predicting, setPredicting] = useState(false);
    // Ollama backends need a local Ollama daemon, so hosted builds ship with
    // 'deberta' only. Override with EXPO_PUBLIC_MODEL_OPTIONS (comma separated).
    const MODEL_OPTIONS = (process.env.EXPO_PUBLIC_MODEL_OPTIONS || 'deberta,phi3,llama3:8b,t5')
        .split(',')
        .map((name) => name.trim())
        .filter(Boolean);
    const [selectedOllamaModel, setSelectedOllamaModel] = useState(MODEL_OPTIONS[0] || 'deberta');
    // Display names only. The wire values stay as-is: server.py routes to the local
    // model by `startswith("deberta")`, so renaming the key would break the request.
    const MODEL_LABELS = {
        deberta: 'deberta-v3-base-grams',
        deberta_local: 'deberta-v3-base-grams',
    };
    const modelLabel = (name) => MODEL_LABELS[name] || name;

    const fetchIngredients = async () => {
        if(useTextInput && !textInput.trim()) return; // 텍스트 활성화되어도 텍스트가 없으면 return(실행 안됌)
        if (!useTextInput && !url.trim()) return; // url 활성화되어도 url가 없으면 return(실행 안됌)
        // Every result below belongs to the previous recipe, so clear it before the
        // request. Otherwise a second parse shows the new chart next to the old
        // gram predictions and a picker still holding an ingredient that is gone.
        setTitle('');
        setGroupData([]);
        setRawIngredients([]);
        setPredictions([]);
        setSelectedIngredient(null);
        setNewAmount('');
        setAdjustedMap({});
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
            setGroupData(
                json.groupsData.map(group =>
                    formatGroupForChart({
                        purpose: group.purpose,
                        chartData: group.chartData,
                        exceptData: group.exceptData,
                    })
                )
            );
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

    // Every chart item, tagged with a unique id and its group. `raw` is not unique:
    // real recipes repeat a line across groups ("1 teaspoon pure vanilla extract" in
    // both the cake and the frosting), and one line can contain another ("1 large egg"
    // inside "1 large egg yolk"). Selecting by raw picked the first match in both
    // cases, so the rescale ran off the wrong ingredient.
    const chartItems = useMemo(
        () => groupData.flatMap((group, groupIndex) =>
            group.chartData.map((item, itemIndex) => ({
                ...item,
                uid: `${groupIndex}-${itemIndex}`,
                purpose: group.purpose || 'Main',
            }))
        ),
        [groupData]
    );
    const multipleGroups = groupData.length > 1;

    const adjustIngredients = () => {
        if (!selectedIngredient || !newAmount) return;
        const parsedNewAmount = parseFloat(newAmount);
        if (Number.isNaN(parsedNewAmount) || !selectedIngredient.quantity) return;
        const ratio = parsedNewAmount / selectedIngredient.quantity;
        const newMap = {};
        groupData.forEach(group => {
            group.chartData.forEach(item => {
                const baseQuantity = Number(item.quantity) || 0;
                const quantity = (baseQuantity * ratio) ;
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
        // A ZeroGPU cold start takes tens of seconds, so the button needs its own
        // spinner — without it the page looks frozen.
        setPredicting(true);
        const res = await fetch(`${BASE_URL}/predict-grams`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                exceptData: exceptDataAll,
                ollamaModel: selectedOllamaModel
            })
        });
        const json = await res.json();
        if (json.error) {
            alert(json.error);
            return;
        }
        setPredictions(json.predicted);
        const predictedMap = new Map(
            json.predicted.map((pred) => [pred.raw, Number(pred.total_prediction) || 0])
        );

        setGroupData((prevGroups) =>
            prevGroups.map((group) => {
                const promotedItems = group.exceptData
                    .map((item) => {
                        const predictedValue = predictedMap.get(item.raw);
                        if (!predictedValue || predictedValue <= 0) return null;
                        return {
                            ...item,
                            value: predictedValue,
                        };
                    })
                    .filter(Boolean);

                const unresolvedExceptData = group.exceptData.filter((item) => {
                    const predictedValue = predictedMap.get(item.raw);
                    return !predictedValue || predictedValue <= 0;
                });

                return formatGroupForChart({
                    ...group,
                    chartData: [...group.chartData, ...promotedItems],
                    exceptData: unresolvedExceptData,
                });
            })
        );
        // Promoted items shift every position in chartData, so the uid held by the
        // current selection would now point at a different ingredient.
        setSelectedIngredient(null);
        setNewAmount('');
        setAdjustedMap({});
    } catch (e) {
        alert(e.message);
        console.log(e);
    } finally {
        setPredicting(false);
    }
    };

    const makescroll = () => {
        return groupData.map((group, index) => {
            if (loading) return null;

            const hasChartData = group.chartData.length > 0
            const hasExceptData = group.exceptData.length > 0
            return ( //  여기서 원래 return이 나와야 되고, 그 return이 나와야되는 이유는 저 map이 돌아가면서 각각 return할게 있어야되기 때문
                <View key={index} style={{ width: CHART_WIDTH, marginHorizontal: 10, marginBottom: 28 }}>
                    {hasChartData && (
                        <>
                            <PieChart
                                data={group.chartData}
                                width={CHART_WIDTH}
                                height={200}
                                chartConfig={{
                                    backgroundColor: COLORS.card,
                                    backgroundGradientFrom: COLORS.card,
                                    backgroundGradientTo: COLORS.card,
                                    decimalPlaces: 2,
                                    color: (opacity = 1) => `rgba(50,100,150,${opacity})`,
                                }}
                                accessor="value"
                                backgroundColor="transparent"
                                paddingLeft="15"
                                hasLegend={false}
                            />
                            {/* ChartData - PieChart 밑으로 이동, 내림차순 정렬 */}
                            <View style={{ marginTop: 10 }}>
                                <Text style={{ fontWeight: '700', fontSize: 15, marginBottom: 6, color: COLORS.text }}>{group.purpose}</Text>
                                {group.chartData.map((item, idx) => (
                                    <View key={idx} style={styles.legendRow}>
                                        <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                                        <Text style={styles.legendText}>
                                            {`${item.percent}%  ${item.name}`}
                                        </Text>
                                    </View>
                                ))}
                            </View>
                        </>
                    )}
                    {/* Except Data */}
                    {hasExceptData && (
                        <View style={{ marginTop: 20 }}>
                            <Text style={styles.sectionTitle}>EXCEPT DATA</Text>
                            {group.exceptData.map((item, idx) => (
                                <Text key={idx} style={styles.listItem}>
                                    {item.quantity ? item.quantity + ' ' : ''}
                                    {item.unit ? item.unit + ' ' : ''}
                                    {item.name}
                                </Text>
                            ))}
                        </View>
                    )}
                </View>
            );
        });
    };
    return (
        <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
            <View style={styles.content}>
                {/* Title */}
                <Text style={styles.title}>Ingredients Pie Chart</Text>
                <Text style={styles.subtitle}>
                    Paste a recipe URL or the raw ingredient lines. Ingredients are converted to
                    weights and drawn as a ratio chart; ambiguous amounts get a gram estimate from
                    the prediction model.
                </Text>

                <View style={styles.card}>
                    <View style={styles.segment}>
                        {[
                            { key: 'url', label: 'URL' },
                            { key: 'text', label: 'Text' },
                        ].map((mode) => {
                            const active = (mode.key === 'text') === useTextInput;
                            return (
                                <Pressable
                                    key={mode.key}
                                    onPress={() => setUseTextInput(mode.key === 'text')}
                                    style={[styles.segmentItem, active && styles.segmentItemActive]}>
                                    <Text style={[styles.segmentLabel, active && styles.segmentLabelActive]}>
                                        {mode.label}
                                    </Text>
                                </Pressable>
                            );
                        })}
                    </View>

                    {useTextInput ? (
                        <TextInput
                            style={[styles.input, styles.textarea]}
                            value={textInput}
                            onChangeText={setTextInput}
                            multiline={true}
                            placeholder={`2 cups flour\n1 tbsp sugar\na pinch of salt`}
                            autoCapitalize="none"
                            autoCorrect={false}
                        />
                    ) : (
                        <TextInput
                            style={[
                                styles.input,
                                !urlTouched && url === SAMPLE_URL && styles.inputSample,
                            ]}
                            value={url}
                            onChangeText={(text) => {
                                setUrlTouched(true);
                                setUrl(text);
                            }}
                            /* Select instead of clear. Clearing looked identical to the
                               untouched field (the placeholder was the same string), so one
                               stray click emptied the URL invisibly and the button turned
                               into a silent no-op. Selecting still lets typing replace it. */
                            onFocus={(e) => {
                                // The click that focuses the field places the caret after this
                                // handler runs, which collapses an immediate select(). Defer it.
                                const input = e.target;
                                if (!urlTouched && url === SAMPLE_URL) {
                                    setTimeout(() => input?.select?.(), 0);
                                }
                            }}
                            placeholder="https://example.com/recipe"
                            autoCapitalize="none"
                            autoCorrect={false}
                        />
                    )}

                    <View style={{ height: 14 }} />
                    {/* Greyed out on an empty field, so pressing it can never look like a
                        dead button — fetchIngredients returns early in that case. */}
                    <ActionButton
                        label="Convert to Chart"
                        onPress={fetchIngredients}
                        disabled={loading || (useTextInput ? !textInput.trim() : !url.trim())}
                    />

                    {loading && (
                        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 14 }}>
                            <ActivityIndicator color={COLORS.accent} />
                            <Text style={[styles.hint, { marginLeft: 8 }]}>Parsing…</Text>
                        </View>
                    )}

                    {/* [LOCAL-ONLY MODE] Keep old EC2 switch for reference only.
                    <Button title={useEC2 ? "Using EC2 (tap to switch to Local)" : "Using Localhost (tap to switch to EC2)"}
                        onPress={() => setUseEC2(prev => !prev)} />
                    */}

                    <View style={{ marginTop: 20 }}>
                        <Text style={styles.sectionTitle}>PREDICTION MODEL</Text>
                        <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                            {MODEL_OPTIONS.map((name) => {
                                const active = name === selectedOllamaModel;
                                return (
                                    <Pressable
                                        key={name}
                                        onPress={() => setSelectedOllamaModel(name)}
                                        style={[styles.chip, active && styles.chipActive]}>
                                        <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{modelLabel(name)}</Text>
                                    </Pressable>
                                );
                            })}
                        </View>
                    </View>
                </View>

                {!useTextInput && (
                    <View style={styles.card}>
                        <Text style={styles.sectionTitle}>WHERE URL MODE WORKS</Text>
                        <SupportedSites baseUrl={BASE_URL} />
                    </View>
                )}

                {/* Piechart + ChartData (legend) */}
                {!loading && groupData.length > 0 && (
                    <>
                        {/* multiple <></>가 있다면 text or {} 그리고 그게 View 같은걸로 감싸져있지 않으면 <></>로 감싸줘야함 */}
                        <View style={styles.card}>
                            {/* Text mode has no recipe title, so skip the heading instead of
                                leaving an empty line. */}
                            {!!title && (
                                <Text style={{ fontSize: 19, fontWeight: '700', marginBottom: 18, color: COLORS.text }}>{title}</Text>
                            )}
                            {/* (Done) raw는 고유값이 아니라 group이 다르면 같은 raw가 나옴 →
                            chartItems의 `${groupIndex}-${itemIndex}` uid로 구별하도록 바꿈 */}
                            <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center' }}>
                                {makescroll()}
                            </View>
                        </View>

                        {/* Adjust ingredient field */}
                        <View style={styles.card}>
                            <Text style={styles.sectionTitle}>ADJUST INGREDIENT</Text>
                            <Text style={[styles.hint, { marginBottom: 12 }]}>
                                Set a new amount for one ingredient and every other amount is rescaled by the same ratio.
                            </Text>
                            <View style={{ borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, marginBottom: 12 }}>
                                <Picker
                                    selectedValue={selectedIngredient?.uid || ''}
                                    style={{ height: 42, width: '100%', borderWidth: 0, backgroundColor: 'transparent', paddingHorizontal: 10, color: COLORS.text }}
                                    onValueChange={(uid) => {
                                        setSelectedIngredient(chartItems.find((item) => item.uid === uid) || null);
                                    }}>
                                    <Picker.Item label="Pick an ingredient" value="" />
                                    {/* The group goes in the label only when there is more than one,
                                        so a single-group recipe keeps the short ingredient names. */}
                                    {chartItems.map((item) => (
                                        <Picker.Item
                                            key={item.uid}
                                            label={multipleGroups ? `${item.name} (${item.purpose})` : item.name}
                                            value={item.uid}
                                        />
                                    ))}
                                </Picker>
                            </View>
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 14 }}>
                                <TextInput
                                    style={[styles.input, { flex: 1 }]}
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

                                    placeholder="New amount"
                                    keyboardType="numeric" // only numbers
                                />
                                <Text style={{ fontSize: 15, color: COLORS.muted, marginLeft: 10, minWidth: 60 }}>
                                    {selectedIngredient?.unit || ''}
                                </Text>
                            </View>

                            <View style={{ flexDirection: 'row' }}>
                                <View style={{ flex: 1 }}>
                                    <ActionButton label="Apply" onPress={adjustIngredients} />
                                </View>
                                <View style={{ width: 10 }} />
                                <View style={{ flex: 1 }}>
                                    <ActionButton
                                        label="Reset"
                                        variant="secondary"
                                        onPress={() => {
                                            setSelectedIngredient(null);
                                            setNewAmount('');
                                            setAdjustedMap({});
                                        }}
                                    />
                                </View>
                            </View>
                        </View>

                        <View style={styles.card}>
                            <Text style={styles.sectionTitle}>GRAM PREDICTION</Text>
                            <Text style={[styles.hint, { marginBottom: 12 }]}>
                                Estimates weights for the except-data items — the ones with no fixed unit
                                conversion — and folds them back into the chart.
                            </Text>
                            <ActionButton
                                label="Predict Grams for Except Data"
                                onPress={fetchPredictions}
                                disabled={predicting}
                                variant="secondary"
                            />

                            {predicting && (
                                <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 14 }}>
                                    <ActivityIndicator color={COLORS.accent} />
                                    <Text style={[styles.hint, { marginLeft: 8 }]}>
                                        Estimating grams… the first run can take a while while the
                                        GPU spins up.
                                    </Text>
                                </View>
                            )}

                            {predictions.length > 0 && (
                                <View style={{ marginTop: 18 }}>
                                    {predictions.map((item, idx) => (
                                        <View key={idx} style={{ marginVertical: 5 }}>
                                            <Text style={styles.listItem}>
                                                {item.raw} → <Text style={{ fontWeight: '700' }}>{item.total_prediction} g</Text>
                                                <Text style={{ color: COLORS.muted }}>{`  (${modelLabel(item.model_used) || 'unknown'})`}</Text>
                                            </Text>
                                            {item.t5_trace && (
                                                <Text style={{ fontSize: 11, color: COLORS.muted }}>
                                                    {`[T5 trace] prompt="${item.t5_trace.input_prompt}" | generated="${item.t5_trace.generated_text}" | parsed=${item.t5_trace.parsed_number}`}
                                                </Text>
                                            )}
                                        </View>
                                    ))}
                                </View>
                            )}
                        </View>

                        {rawIngredients.length > 0 && (
                            <View style={styles.card}>
                                <Text style={styles.sectionTitle}>RAW INGREDIENTS</Text>
                                {rawIngredients.map((line, idx) => {
                                    const adjusted = adjustedMap[line]; // 괄호 → 대괄호로 수정
                                    return (
                                        <View key={idx} style={{ flexDirection: 'row', justifyContent: adjusted ? 'space-between' : 'flex-start', marginBottom: 5, width: '100%' }}>
                                            <Text style={[styles.listItem, { flex: 1 }]}>{line}</Text>
                                            {adjusted && (

                                                <Text style={[styles.listItem, { flex: 1, textAlign: 'right', color: COLORS.accent }]}> →
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
            </View>
        </ScrollView>

    );

}
