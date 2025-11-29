from core.refactorings.function_prototype.prototype_utils import PrototypeParser, PrototypeModifier


def test_parsing():
    test_cases = [
        {
            'name': 'Simple function',
            'prototype': 'int add(int a, int b);',
            'expected_return': 'int',
            'expected_name': 'add',
            'expected_params': [('int', 'a'), ('int', 'b')]
        },
        {
            'name': 'Function with qualifiers',
            'prototype': 'inline static void process(const std::string& str) const;',
            'expected_return': 'void',
            'expected_name': 'process',
            'expected_params': [('const std::string&', 'str')]
        },
        {
            'name': 'Method with namespace',
            'prototype': 'std::string MyClass::getName() const;',
            'expected_return': 'std::string',
            'expected_name': 'getName',
            'expected_params': []
        },
        {
            'name': 'Template parameters',
            'prototype': 'bool compare(std::vector<int> a, std::map<std::string, int> b);',
            'expected_return': 'bool',
            'expected_name': 'compare',
            'expected_params': [('std::vector<int>', 'a'), ('std::map<std::string, int>', 'b')]
        },
        {
            'name': 'No parameters',
            'prototype': 'void clear();',
            'expected_return': 'void',
            'expected_name': 'clear',
            'expected_params': []
        },
    ]

    print("Testing PrototypeParser...")
    for test in test_cases:
        print(f"\n  Test: {test['name']}")
        print(f"    Input: {test['prototype']}")

        return_type = PrototypeParser.extract_return_type(test['prototype'])
        func_name = PrototypeParser.extract_function_name(test['prototype'])
        params = PrototypeParser.extract_parameters(test['prototype'])

        print(f"    Return type: {return_type} (expected: {test['expected_return']})")
        print(f"    Function name: {func_name} (expected: {test['expected_name']})")
        print(f"    Parameters: {params} (expected: {test['expected_params']})")

        assert return_type == test['expected_return'], f"Return type mismatch: {return_type} != {test['expected_return']}"
        assert func_name == test['expected_name'], f"Function name mismatch: {func_name} != {test['expected_name']}"
        assert params == test['expected_params'], f"Parameters mismatch: {params} != {test['expected_params']}"

        print(f"    [PASS]")

    print("\n[All parsing tests passed!]\n")


def test_modification():
    test_cases = [
        {
            'name': 'Change return type',
            'prototype': 'int add(int a, int b);',
            'operation': lambda p: PrototypeModifier.replace_return_type(p, 'double'),
            'expected': 'double add(int a, int b);'
        },
        {
            'name': 'Change function name',
            'prototype': 'void process(std::string str);',
            'operation': lambda p: PrototypeModifier.replace_function_name(p, 'handle'),
            'expected': 'void handle(std::string str);'
        },
        {
            'name': 'Change parameter type',
            'prototype': 'bool check(int value, std::string name);',
            'operation': lambda p: PrototypeModifier.replace_parameter_type(p, 0, 'long'),
            'expected': 'bool check(long value, std::string name);'
        },
        {
            'name': 'Rename parameter',
            'prototype': 'void set(int x);',
            'operation': lambda p: PrototypeModifier.replace_parameter_name(p, 0, 'value'),
            'expected': 'void set(int value);'
        },
        {
            'name': 'Add parameter at end',
            'prototype': 'int compute(int a);',
            'operation': lambda p: PrototypeModifier.add_parameter(p, 'int', 'b', -1),
            'expected': 'int compute(int a, int b);'
        },
        {
            'name': 'Remove parameter',
            'prototype': 'void func(int a, int b, int c);',
            'operation': lambda p: PrototypeModifier.remove_parameter(p, 1),
            'expected': 'void func(int a, int c);'
        },
    ]

    print("Testing PrototypeModifier...")
    for test in test_cases:
        print(f"\n  Test: {test['name']}")
        print(f"    Input: {test['prototype']}")

        result = test['operation'](test['prototype'])

        print(f"    Result: {result}")
        print(f"    Expected: {test['expected']}")

        assert result == test['expected'], f"Modification mismatch: {result} != {test['expected']}"

        print(f"    [PASS]")

    print("\n[All modification tests passed!]\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Function Prototype Utilities Test Suite")
    print("=" * 60)

    test_parsing()
    test_modification()

    print("=" * 60)
    print("[ALL TESTS PASSED]")
    print("=" * 60)
