#include <iostream>  // For input/output
#include <vector>    // For using std::vector
#include <algorithm> // For sorting
#include <fstream>   // For file handling

using namespace std;

void writeToFile(const string& filename, const vector<int>& numbers) {
    ofstream outFile(filename);
    if (!outFile) {
        cerr << "Error opening file for writing!" << endl;
        return;
    }
    for (int num : numbers) {
        outFile << num << " ";
    }
    outFile.close();
    cout << "Numbers written to " << filename << endl;
}

void readFromFile(const string& filename) {
    ifstream inFile(filename);
    if (!inFile) {
        cerr << "Error opening file for reading!" << endl;
        return;
    }
    cout << "Reading numbers from " << filename << ": ";
    int num;
    while (inFile >> num) {
        cout << num << " ";
    }
    cout << endl;
    inFile.close();
}

int main() {
    // Create a vector of integers
    vector<int> numbers = {42, 16, 73, 8, 23};

    // Print the original vector
    cout << "Original numbers: ";
    for (int num : numbers) {
        cout << num << " ";
    }
    cout << endl;

    // Sort the vector
    sort(numbers.begin(), numbers.end());

    // Print the sorted vector
    cout << "Sorted numbers: ";
    for (int num : numbers) {
        cout << num << " ";
    }
    cout << endl;

    // Write the sorted numbers to a file
    string filename = "numbers.txt";
    writeToFile(filename, numbers);

    // Read the numbers back from the file
    readFromFile(filename);

    return 0;
}
