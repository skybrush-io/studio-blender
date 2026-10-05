// Independent libskybrush binary trajectory reader for conversion diagnostics.
#include <skybrush/trajectory.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    std::ifstream file(argv[1], std::ios::binary);
    if (!file) return 2;
    std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(file)), {});
    auto* trajectory = sb_trajectory_new();
    if (!trajectory) return 3;
    auto error = sb_trajectory_update_from_binary_file_in_memory(
        trajectory, bytes.data(), bytes.size());
    if (error) { SB_XDECREF(trajectory); return 4; }
    std::cout << sb_trajectory_get_total_duration_msec(trajectory) << "\n";
    SB_XDECREF(trajectory);
}
