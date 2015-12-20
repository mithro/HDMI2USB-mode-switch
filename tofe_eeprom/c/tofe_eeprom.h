#ifndef __OPSIS_EEPROM_H
#define __OPSIS_EEPROM_H

#ifdef __SDCC
#include "sdcc_stdin.h"
#else
#include <stdint.h>
#endif  // __SDCC

const char[] tofe_magic = "TOFE\0";
const char[] tofe_ragic = "\0EFOT";

struct tofe_header {
	char magic[5];
	__u8 version;
	__u8 atoms;
	__u8 crc8;
	__u32 data_len;
	__u8 data[];
} __attribute__ ((packed));

__u8 tofe_calculate_crc(const char* tofe_header);

/* Common to all atoms */
struct tofe_atom_header {
	__u8 type;
	__u8 len;
};

/* Non-decoded atom */
struct tofe_atom {
	struct tofe_atom_header;
	__u8 data[];
} __attribute__ ((packed));

/* Atom Formats */
enum tofe_atomfmt {
	ATOM_FMT_invalid	= 0xff,
	ATOM_FMT_string		= 0x00,
	ATOM_FMT_url		= 0x10,
	ATOM_FMT_relative_url	= 0x20,
	ATOM_FMT_expand_int	= 0x30,
	ATOM_FMT_license	= 0x40,
	ATOM_FMT_size_offset	= 0x50,
	ATOM_FMT_binary_blob	= 0x60,
};

#define TOFE_EXTRA_LEN(x) \
	(sizeof(x) - sizeof(tofe_atom_header))

const struct tofe_atom* tofe_atom_get(__u8 index, const struct tofe_header* hdr);

#define DEFINE_TOFE_ATOM_GET_FMT(name) \
	inline const struct tofe_atomfmt_ ## name * tofe_atom_get_ ## name (__u8 index, const struct tofe_header* hdr) { \
		const struct tofe_atom* atom = tofe_atom_get(index, hdr); \
		assert(ATOM_FMT_ ## name == tofe_atomfmt(atom); \
		return (struct tofe_atomfmt_ ## name *)(atom); \
	}

DEFINE_TOFE_ATOM_GET_FMT(string);
DEFINE_TOFE_ATOM_GET_FMT(url);
DEFINE_TOFE_ATOM_GET_FMT(relative_url);
DEFINE_TOFE_ATOM_GET_FMT(expand_int);
DEFINE_TOFE_ATOM_GET_FMT(license);
DEFINE_TOFE_ATOM_GET_FMT(size_offset);

char* tofe_atom_print(char* ptr, const struct tofe_atom* atom);
#define DECLARE_TOFE_ATOM_GET_FMT(name) \
	char* tofe_atom_print_ ## name (const struct tofe_atomfmt_ ## name * atom);

/* String Format */
struct tofe_atomfmt_string {
	struct tofe_atom_header;
	char str[];
} __attribute__ ((packed));

/* URL Format */
struct tofe_atomfmt_url {
	struct tofe_atom_header;
	char url[];
} __attribute__ ((packed));

/* Relative URL Format */
struct tofe_atomfmt_relative_url {
	struct tofe_atom_header;
	__u8 atom_index;
	char rurl[];
} __attribute__ ((packed));

/* Expand Int Format */
struct tofe_atomfmt_expand_int {
	struct tofe_atom_header;
	__u8 data[];
} __attribute__ ((packed));

#define tofe_atomfmt_expand_int_get(atom_ptr, value) \
	do { \
		assert(atom.len <= sizeof(value)); \
		value = 0; \
		for (size_t i = 0; i < (atom)->len; i++) { \
			value |= ((typeof(value))(atom)->data[i]) << (i*8); \
		} \
	} while(false)

/* License Format */
struct tofe_atomfmt_license {
	struct tofe_atom_header;
	__u8 license;
} __attribute__ ((packed));

#define TOFE_LICENSE_ENUM(type, version) \
	type << 3 | version

enum tofe_atomfmt_license_enum {
        // MIT
        MIT             = TOFE_LICENSE_ENUM(1, 1),
        // BSD
        BSD_simple      = TOFE_LICENSE_ENUM(2, 1),
        BSD_new         = TOFE_LICENSE_ENUM(2, 2),
        BSD_isc         = TOFE_LICENSE_ENUM(2, 3),
        // Apache
        Apache_v2       = TOFE_LICENSE_ENUM(3, 1),
        // GPL
        GPL_v2          = TOFE_LICENSE_ENUM(4, 1),
        GPL_v3          = TOFE_LICENSE_ENUM(4, 2),
        // LGPL
        LGPL_v21        = TOFE_LICENSE_ENUM(5, 1),
        LGPL_v3         = TOFE_LICENSE_ENUM(5, 2),
        // CC0
        CC0_v1          = TOFE_LICENSE_ENUM(6, 1),
        // CC BY
        CC_BY_v10       = TOFE_LICENSE_ENUM(7, 1),
        CC_BY_v20       = TOFE_LICENSE_ENUM(7, 2),
        CC_BY_v25       = TOFE_LICENSE_ENUM(7, 3),
        CC_BY_v30       = TOFE_LICENSE_ENUM(7, 4),
        CC_BY_v40       = TOFE_LICENSE_ENUM(7, 5),
        // CC BY-SA
        CC_BY_SA_v10    = TOFE_LICENSE_ENUM(8, 1),
        CC_BY_SA_v20    = TOFE_LICENSE_ENUM(8, 2),
        CC_BY_SA_v25    = TOFE_LICENSE_ENUM(8, 3),
        CC_BY_SA_v30    = TOFE_LICENSE_ENUM(8, 4),
        CC_BY_SA_v40    = TOFE_LICENSE_ENUM(8, 5),
        // TAPR
        TAPR_v10        = TOFE_LICENSE_ENUM(9, 1),
        // CERN
        CERN_v11        = TOFE_LICENSE_ENUM(10, 1),
        CERN_v12        = TOFE_LICENSE_ENUM(10, 2),
        // Other
        Invalid         = 0,
        Proprietary     = 0xff
};

const char* tofe_atomfmt_license_name(const struct tofe_atomfmt_license* atom);
const char* tofe_atomfmt_license_version(const struct tofe_atomfmt_license* atom);

/* EEPROM Atom */
#define DEFINE_TOFE_ATOM_SIZE_OFFSET(name, type) \
	struct tofe_atomfmt_size_offset_ ## name { \
		struct tofe_atom_header; \
		type offset; \
		type size; \
	} __attribute__ ((packed))

DEFINE_TOFE_ATOM_SIZE_OFFSET(small, __u8);
DEFINE_TOFE_ATOM_SIZE_OFFSET(medium, __u8);
DEFINE_TOFE_ATOM_SIZE_OFFSET(large, __u8);

#define tofe_atomfmt_size_offset_get_size(atom_ptr, value) \
	do { \
		assert(sizeof(value) > (atom_ptr)->len / 2); \
		switch ((atom_ptr)->len) { \
		case 0x2: \
			((tofe_atomfmt_size_offset_small)(atom_ptr))->size; \
			break; \
		case 0x4: \
			((tofe_atomfmt_size_offset_medium)(atom_ptr))->size; \
			break; \
		case 0x8: \
			((tofe_atomfmt_size_offset_large)(atom_ptr))->size; \
			break; \
		default: \
			assert(false); \
		} \
	} while(false)

#define tofe_atomfmt_size_offset_get_offset(atom_ptr, value) \
	do { \
		assert(sizeof(value) > (atom_ptr)->len / 2); \
		switch ((atom_ptr)->len) { \
		case 0x2: \
			((tofe_atomfmt_size_offset_small)(atom_ptr))->offset; \
			break; \
		case 0x4: \
			((tofe_atomfmt_size_offset_medium)(atom_ptr))->offset; \
			break; \
		case 0x8: \
			((tofe_atomfmt_size_offset_large)(atom_ptr))->offset; \
			break; \
		default: \
			assert(false); \
		} \
	} while(false)


// Specific atom types
#define TOFE_ATOM_TYPE_ENUM(string, url, relative_url, expand_int, license, size_offset, binary_blob) \
	(( \
		(string 	? ATOM_FMT_string	: 0) | \
		(url		? ATOM_FMT_url		: 0) | \
		(relative_url	? ATOM_FMT_relative_url	: 0) | \
		(expand_int	? ATOM_FMT_expand_int	: 0) | \
		(license	? ATOM_FMT_license	: 0) | \
		(size_offset	? ATOM_FMT_size_offset	: 0) | \
		(binary_blob	? ATOM_FMT_binary_blob	: 0) \
	) << 4) | \
	(string | url | relative_url | expand_int | license | size_offset | binary_blob)

enum tofe_atom_type {
	ATOM_INVALID_x00 = 0,
	ATOM_INVALID_xFF = 0xff,
	//                                            /------------- String Format
	//                                            | /----------- URL Format
	//                                            | | /--------- Relative URL Format
	//                                            | | | /------- Expand Int Format
	//                                            | | | | /----- License Format
	//                                            | | | | | /--- Size Offset Format
	// Product identification atoms               | | | | | | /- Binary Block Format
	ATOM_DESIGNER_ID	= TOFE_ATOM_TYPE_ENUM(_,1,_,_,_,_,_),
	ATOM_MANUFACTURER_ID	= TOFE_ATOM_TYPE_ENUM(_,2,_,_,_,_,_),
	ATOM_PRODUCT_ID		= TOFE_ATOM_TYPE_ENUM(_,3,_,_,_,_,_),
	ATOM_PRODUCT_VERSION	= TOFE_ATOM_TYPE_ENUM(1,_,_,_,_,_,_),
	ATOM_PRODUCT_SERIAL	= TOFE_ATOM_TYPE_ENUM(2,_,_,_,_,_,_),
	ATOM_PRODUCT_PART	= TOFE_ATOM_TYPE_ENUM(3,_,_,_,_,_,_),
	// Auxiliary atoms
	ATOM_AUX_URL		= TOFE_ATOM_TYPE_ENUM(_,4,_,_,_,_,_),
	// PCB related atoms
	ATOM_PCB_REPO		= TOFE_ATOM_TYPE_ENUM(_,_,1,_,_,_,_),
	ATOM_PCB_REV		= TOFE_ATOM_TYPE_ENUM(4,_,_,_,_,_,_),
	ATOM_PCB_LICENSE	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,1,_,_),
	ATOM_PCB_PROD_BATCH	= TOFE_ATOM_TYPE_ENUM(_,_,_,1,_,_,_),
	ATOM_PCB_POP_BATCH	= TOFE_ATOM_TYPE_ENUM(_,_,_,2,_,_,_),
	// Firmware related atoms
	ATOM_FIRMWARE_DESC	= TOFE_ATOM_TYPE_ENUM(5,_,_,_,_,_,_),
	ATOM_FIRMWARE_REPO	= TOFE_ATOM_TYPE_ENUM(_,_,2,_,_,_,_),
	ATOM_FIRMWARE_REV	= TOFE_ATOM_TYPE_ENUM(6,_,_,_,_,_,_),
	ATOM_FIRMWARE_LICENSE	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,2,_,_),
	ATOM_FIRMWARE_PROG_ON	= TOFE_ATOM_TYPE_ENUM(_,_,_,3,_,_,_),
	// EEPROM related atoms
	ATOM_EEPROM_SIZE	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,_,1,_),
	ATOM_EEPROM_VENDOR	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,_,2,_),
	ATOM_EEPROM_TOFE	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,_,3,_),
	ATOM_EEPROM_USER	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,_,4,_),
	ATOM_EEPROM_GUID	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,_,5,_),
	ATOM_EEPROM_HOLE	= TOFE_ATOM_TYPE_ENUM(_,_,_,_,_,6,_),
	ATOM_EEPROM_PART	= TOFE_ATOM_TYPE_ENUM(7,_,_,_,_,_,_),
	// Informational Atoms
	ATOM_INFO_SAMPLE_CODE	= TOFE_ATOM_TYPE_ENUM(_,_,3,_,_,_,_),
	ATOM_INFO_DOCS		= TOFE_ATOM_TYPE_ENUM(_,_,4,_,_,_,_),
};

const char* tofe_atom_typeenum_str(enum tofe_atom_type type);
inline const char* tofe_atom_type_str(const struct tofe_atom* atom) {
	return tofe_atom_typeenum_str(atom->type);
}

inline enum tofe_atomfmt tofe_atomfmt_for_type(enum tofe_atom_type type) {
	return (type & 0xf0);
}
inline enum tofe_atomfmt tofe_atomfmt(const struct tofe_atom* atom) {
	return tofe_atomfmt_for_type(atom->type);
}

#endif  // __TOFE_EEPROM
