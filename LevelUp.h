#ifndef LEVELUP_H
#define LEVELUP_H

namespace LevelUp {

template<typename T>
class unique_ptr {
private:
    T* ptr_;

public:
    unique_ptr() : ptr_(nullptr) {}

    explicit unique_ptr(T* p) : ptr_(p) {}

    ~unique_ptr() {
        delete ptr_;
    }

    unique_ptr(const unique_ptr&) = delete;
    unique_ptr& operator=(const unique_ptr&) = delete;

    unique_ptr(unique_ptr&& other) : ptr_(other.ptr_) {
        other.ptr_ = nullptr;
    }

    unique_ptr& operator=(unique_ptr&& other) {
        if (this != &other) {
            delete ptr_;
            ptr_ = other.ptr_;
            other.ptr_ = nullptr;
        }
        return *this;
    }

    T* get() const {
        return ptr_;
    }

    T* release() {
        T* temp = ptr_;
        ptr_ = nullptr;
        return temp;
    }

    void reset(T* p = nullptr) {
        delete ptr_;
        ptr_ = p;
    }

    T& operator*() const {
        return *ptr_;
    }

    T* operator->() const {
        return ptr_;
    }

    explicit operator bool() const {
        return ptr_ != nullptr;
    }
};

template<typename T>
class unique_ptr<T[]> {
private:
    T* ptr_;

public:
    unique_ptr() : ptr_(nullptr) {}

    explicit unique_ptr(T* p) : ptr_(p) {}

    ~unique_ptr() {
        delete[] ptr_;
    }

    unique_ptr(const unique_ptr&) = delete;
    unique_ptr& operator=(const unique_ptr&) = delete;

    unique_ptr(unique_ptr&& other) : ptr_(other.ptr_) {
        other.ptr_ = nullptr;
    }

    unique_ptr& operator=(unique_ptr&& other) {
        if (this != &other) {
            delete[] ptr_;
            ptr_ = other.ptr_;
            other.ptr_ = nullptr;
        }
        return *this;
    }

    T* get() const {
        return ptr_;
    }

    T* release() {
        T* temp = ptr_;
        ptr_ = nullptr;
        return temp;
    }

    void reset(T* p = nullptr) {
        delete[] ptr_;
        ptr_ = p;
    }

    T& operator[](size_t i) const {
        return ptr_[i];
    }

    explicit operator bool() const {
        return ptr_ != nullptr;
    }
};

template<typename T, typename... Args>
unique_ptr<T> make_unique(Args&&... args) {
    return unique_ptr<T>(new T(static_cast<Args&&>(args)...));
}

template<typename T>
unique_ptr<T> make_unique(size_t size) {
    return unique_ptr<T>(new typename std::remove_extent<T>::type[size]());
}

}

#endif
