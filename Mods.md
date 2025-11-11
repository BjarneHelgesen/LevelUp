1. Document functions and classes using doxygen syntax in the header files.
2. Add override keyword to methods
3. Add explicit keyword to constructors
4. Add const keyword to methods
5. Add noexcept keyword to methods 
6. Make local variables const
7. Make pointer and reference parameters const
8. Replace pointer parameters with references
9. Use new and delete instead of malloc and free
10. Delete commented out code, unless it is usage instruction
11. Delete dead code
12. Extract inlined functions from long functions
14. Use range-based for loops on containers
15. When new throws, dont check that it is non-null
16. Use nullptr for pointers, not NULL macro or 0
17. Use custom C::string class to wrap char * using std::string syntax
18. Use owner<T> and nonowner<T> as pointer parameter to classify T* parameters
19. Replace pointer arithmetic with span<T>
20. Silence warnings without changing behaviour
21. Spell out symbols that are overly abbreviated, e.g. scr, idx, px, pt become screen, index, pixel, point
22. Remove hungarian notation, (C for class, lpzstr for string, i for integer)
23. Enforce member and static naming (e,g. m_ for member, s_ for staticj
24. Simplify boolean expressions
25. 

