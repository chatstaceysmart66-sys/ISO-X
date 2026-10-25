// ISO-X watermark module 0.3.1 — attribution only.
// Integrity is enforced outside this module by the signed module file,
// initramfs verification, and (when configured) the kernel's module-signing policy.
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/string.h>
#include "watermark_bytes.h"

#define ISOX_WM_XOR_MASK 0x5a

static int __init isox_watermark_init(void)
{
    char text[sizeof(isox_watermark_text) + 1];
    size_t i;

    // Decode exactly the mask used by scripts/encode-watermark.py. This is
    // obfuscation for a display label, not encryption or a security boundary.
    for (i = 0; i < sizeof(isox_watermark_text); i++)
        text[i] = (char)(isox_watermark_text[i] ^ ISOX_WM_XOR_MASK);
    text[sizeof(isox_watermark_text)] = '\0';
    pr_info("ISO-X watermark active: %s\n", text);
    memzero_explicit(text, sizeof(text));
    return 0;
}

static void __exit isox_watermark_exit(void)
{
    pr_info("ISO-X watermark unloaded\n");
}

module_init(isox_watermark_init);
module_exit(isox_watermark_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ISO-X attribution watermark v0.3.1");
MODULE_VERSION("0.3.1");
