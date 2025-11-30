from core.refactorings.function_prototype.prototype_utils import PrototypeParser, PrototypeModifier, PrototypeBuilder, Parameter
from core.refactorings.function_prototype.prototype_change_spec import PrototypeChangeSpec


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


def test_parse_and_build():
    """Test parsing prototypes into components and rebuilding them."""
    test_cases = [
        {
            'name': 'Simple function',
            'prototype': 'int add(int a, int b);',
        },
        {
            'name': 'Function with leading qualifiers',
            'prototype': 'inline static void process(const std::string& str);',
        },
        {
            'name': 'Function with trailing qualifiers',
            'prototype': 'std::string getName() const noexcept;',
        },
        {
            'name': 'Function with default parameters',
            'prototype': 'void configure(int timeout = 30, bool verbose = false);',
        },
        {
            'name': 'Function with all qualifiers',
            'prototype': 'inline virtual int compute(double x, double y = 1.0) const override;',
        },
        {
            'name': 'Method with namespace',
            'prototype': 'std::string MyClass::getName() const;',
        },
        {
            'name': 'Function ending with brace',
            'prototype': 'void empty() {',
        },
    ]

    print("Testing parse_prototype and build...")
    for test in test_cases:
        print(f"\n  Test: {test['name']}")
        print(f"    Input: {test['prototype']}")

        # Parse the prototype
        components = PrototypeParser.parse_prototype(test['prototype'])
        assert components is not None, f"Failed to parse: {test['prototype']}"

        # Rebuild the prototype
        rebuilt = PrototypeBuilder.build(components)
        print(f"    Rebuilt: {rebuilt}")

        # Parse the rebuilt version
        components2 = PrototypeParser.parse_prototype(rebuilt)
        assert components2 is not None, f"Failed to parse rebuilt: {rebuilt}"

        # Verify key components match
        assert components.return_type == components2.return_type, "Return type mismatch"
        assert components.function_name == components2.function_name, "Function name mismatch"
        assert len(components.parameters) == len(components2.parameters), "Parameter count mismatch"
        assert components.terminator == components2.terminator, "Terminator mismatch"

        print(f"    Leading qualifiers: {components.leading_qualifiers}")
        print(f"    Return type: {components.return_type}")
        print(f"    Function name: {components.function_name}")
        print(f"    Parameters: {[(p.type, p.name, p.default_value) for p in components.parameters]}")
        print(f"    Trailing qualifiers: {components.trailing_qualifiers}")
        print(f"    Terminator: '{components.terminator}'")
        print(f"    [PASS]")

    print("\n[All parse and build tests passed!]\n")


def test_modify_components():
    """Test modifying prototype components."""
    test_cases = [
        {
            'name': 'Change return type',
            'prototype': 'int add(int a, int b);',
            'change_spec': lambda: PrototypeChangeSpec().set_return_type('double'),
            'verify': lambda result: 'double add(' in result and result != 'int add('
        },
        {
            'name': 'Change function name',
            'prototype': 'void process(std::string str);',
            'change_spec': lambda: PrototypeChangeSpec().set_function_name('handle'),
            'verify': lambda result: 'handle(' in result and 'process(' not in result
        },
        {
            'name': 'Change parameter type',
            'prototype': 'bool check(int value, std::string name);',
            'change_spec': lambda: PrototypeChangeSpec().change_parameter_type(0, 'long'),
            'verify': lambda result: 'long value' in result
        },
        {
            'name': 'Change parameter name',
            'prototype': 'void set(int x);',
            'change_spec': lambda: PrototypeChangeSpec().change_parameter_name(0, 'value'),
            'verify': lambda result: 'int value' in result and 'int x' not in result
        },
        {
            'name': 'Add parameter',
            'prototype': 'int compute(int a);',
            'change_spec': lambda: PrototypeChangeSpec().add_parameter('int', 'b', -1),
            'verify': lambda result: 'int a, int b' in result
        },
        {
            'name': 'Remove parameter',
            'prototype': 'void func(int a, int b, int c);',
            'change_spec': lambda: PrototypeChangeSpec().remove_parameter(1),
            'verify': lambda result: 'int a, int c' in result and 'int b' not in result
        },
        {
            'name': 'Preserve default values',
            'prototype': 'void configure(int timeout = 30, bool verbose = false);',
            'change_spec': lambda: PrototypeChangeSpec().change_parameter_type(0, 'long'),
            'verify': lambda result: 'long timeout = 30' in result and 'bool verbose = false' in result
        },
        {
            'name': 'Preserve qualifiers when changing return type',
            'prototype': 'inline static int compute(double x);',
            'change_spec': lambda: PrototypeChangeSpec().set_return_type('double'),
            'verify': lambda result: 'inline static double' in result
        },
    ]

    print("Testing modify_components...")
    for test in test_cases:
        print(f"\n  Test: {test['name']}")
        print(f"    Input: {test['prototype']}")

        # Parse the prototype
        components = PrototypeParser.parse_prototype(test['prototype'])
        assert components is not None, f"Failed to parse: {test['prototype']}"

        # Apply changes
        change_spec = test['change_spec']()
        modified_components = PrototypeBuilder.modify_components(components, change_spec)

        # Rebuild
        result = PrototypeBuilder.build(modified_components)
        print(f"    Result: {result}")

        # Verify
        assert test['verify'](result), f"Verification failed for: {result}"
        print(f"    [PASS]")

    print("\n[All modify components tests passed!]\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Function Prototype Utilities Test Suite")
    print("=" * 60)

    test_parsing()
    test_modification()
    test_parse_and_build()
    test_modify_components()

    print("=" * 60)
    print("[ALL TESTS PASSED]")
    print("=" * 60)
