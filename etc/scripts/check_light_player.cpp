// Integration adapter for the public libskybrush LED player.
// Build with its include directory and static library; pass raw LED bytes.
#include <skybrush/lights.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

int main(int argc, char** argv) {
    if (argc < 3) return 2;
    std::ifstream file(argv[1], std::ios::binary);
    if (!file) return 2;
    std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(file)), {});
    auto* program = sb_light_program_new();
    if (!program) return 3;
    if (sb_light_program_update_from_buffer(program, bytes.data(), bytes.size())) return 4;
    sb_light_player_t player;
    if (sb_light_player_init(&player, program)) return 5;
    for (int i = 2; i < argc; ++i) {
        auto t = std::stoul(argv[i]);
        auto c = sb_light_player_get_color_at(&player, t);
        std::cout << t << " " << int(c.red) << " " << int(c.green) << " " << int(c.blue) << "\n";
    }
    sb_light_player_destroy(&player);
    SB_XDECREF(program);
}
