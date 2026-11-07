// W861: mxDataGen 的最小实现 -- 只提供 client 链接时需要的 mxScaleLayoutForArchName。
//
// 为什么不用原版 clients/common/src/mxDataGen.cpp：那个文件依赖 mxDataGenerator 兄弟仓库
// （DGen::ocp_* 一族），本树里没有、166 也拉不到 GitHub。
// 而 client 只用到这一个函数，实现仅 8 行、无外部依赖：
//     gfx950 -> GFX950, gfx1250 -> GFX1250, 其余 -> None
// gfx906 落在 None（本来就没有 MX 缩放布局），语义完全正确。
#include "mxDataGen.hpp"

MXScaleLayout mxScaleLayoutForArchName(std::string_view archName)
{
    if(archName.find("gfx950") != std::string_view::npos)
        return MXScaleLayout::GFX950;
    if(archName.find("gfx1250") != std::string_view::npos)
        return MXScaleLayout::GFX1250;
    return MXScaleLayout::None;
}
