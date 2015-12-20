
#include "tofe_eeprom.h"

__u8 tofe_calculate_crc(const char* tofe_header) {
};

const struct tofe_atom* tofe_atom_get(__u8 index, const struct tofe_header* hdr) {
	const struct tofe_atom* atom = (const struct tofe_atom*)(&(hdr->data[0]));
	for (__u8 i = 0; i < index; i++) {
		assert((atom + atom->len) < (hdr->data + hdr->data_len));
		atom += atom->len;
		atom += sizeof(tofe_atom_header);
	}
	return atom;
}


const char* tofe_atom_license_name(const struct tofe_atom_license* atom) {
	switch((enum tofe_atom_license_enum)(atom->license)) {
        // MIT
	case MIT:
		return "MIT";
        // BSD
	case BSD_simple:
	case BSD_new:
	case BSD_isc:
		return "BSD";
        // Apache
	case Apache_v2:
		return "Apache";
        // GPL
	case GPL_v2:
	case GPL_v3:
		return "GPL";
        // LGPL
	case LGPL_v21:
	case LGPL_v3:
		return "LGPL";
        // CC0
	case CC0_v1:
		return "CC0";
        // CC BY
	case CC_BY_v10:
	case CC_BY_v20:
	case CC_BY_v25:
	case CC_BY_v30:
	case CC_BY_v40:
		return "CC BY";
        // CC BY-SA
	case CC_BY_SA_v10:
	case CC_BY_SA_v20:
	case CC_BY_SA_v25:
	case CC_BY_SA_v30:
	case CC_BY_SA_v40:
		return "CC BY-SA";
        // TAPR
	case TAPR_v10:
		return "TAPR";
        // CERN
	case CERN_v11:
	case CERN_v12:
		return "CERN";
        // Other
	case Invalid:
		return "Invalid";
	case Proprietary:
		return "Proprietary";
#ifdef NDEBUG
	default:
		return "Unknown";
#endif
	}
}

const char* tofe_atom_license_version(const struct tofe_atom_license* atom) {
	switch((enum tofe_atom_license_enum)(atom->license)) {
        // No version
	case MIT:
	case Proprietary:
		return "";
        // BSD
	case BSD_simple:
		return "Simple";
	case BSD_new:
		return "New";
	case BSD_isc:
		return "ISC";
        // v1.0
	case CC0_v1:
	case CC_BY_v10:
	case CC_BY_SA_v10:
	case TAPR_v10:
		return "1.0";
        // v1.1
	case CERN_v11:
		return "1.1";
        // v1.2
	case CERN_v12:
		return "1.2";
        // v2.0
	case Apache_v2:
	case GPL_v2:
	case CC_BY_v20:
	case CC_BY_SA_v20:
		return "2.0";
        // v2.1
	case LGPL_v21:
		return "2.1";
	// v2.5
	case CC_BY_v25:
	case CC_BY_SA_v25:
		return "2.5";
        // v3.0
	case GPL_v3:
	case LGPL_v3:
	case CC_BY_v30:
	case CC_BY_SA_v30:
		return "3.0";
        // v4.0
	case CC_BY_v40:
	case CC_BY_SA_v40:
		return "4.0";
	// Invalid
	case Invalid:
		return "Invalid";
#ifdef NDEBUG
	default:
		return "Unknown";
#endif
	}
}

const char* tofe_atom_type_enum_str(enum tofe_atom_type_enum type) {
	switch(type) {
	case ATOM_INVALID_x00:
	case ATOM_INVALID_xFF:
		return "Invalid";
	// Product identification atoms
	case ATOM_DESIGNER_ID:
		return "Designer";
	case ATOM_MANUFACTURER_ID:
		return "Manufacturer";
	case ATOM_PRODUCT_ID:
		return "Product";
	case ATOM_PRODUCT_VERSION:
		return "Version";
	case ATOM_PRODUCT_SERIAL:
		return "Serial";
	case ATOM_PRODUCT_PART:
		return "Part #";
	// Auxiliary atoms
	case ATOM_AUX_URL:
		return "";
	// PCB related atoms
	case ATOM_PCB_REPO:
		return "PCB Repository";
	case ATOM_PCB_REV:
		return "PCB Revision";
	case ATOM_PCB_LICENSE:
		return "PCB License";
	case ATOM_PCB_PROD_BATCH:
		return "PCB Production Batch";
	case ATOM_PCB_POP_BATCH:
		return "PCB Population Batch";
	// Firmware related atoms
	case ATOM_FIRMWARE_DESC:
		return "Firmware";
	case ATOM_FIRMWARE_REPO:
		return "Firmware Repository";
	case ATOM_FIRMWARE_REV:
		return "Firmware Revision";
	case ATOM_FIRMWARE_LICENSE:
		return "Firmware License";
	case ATOM_FIRMWARE_PROG_ON:
		return "Firmware Programmed on";
	// EEPROM related atoms
	case ATOM_EEPROM_SIZE:
		return "EEPROM Size";
	case ATOM_EEPROM_VENDOR:
		return "EEPROM Vendor Area";
	case ATOM_EEPROM_TOFE:
		return "EEPROM TOFE Area";
	case ATOM_EEPROM_USER:
		return "EEPROM USER Area";
	case ATOM_EEPROM_GUID:
		return "EEPROM GUID";
	case ATOM_EEPROM_HOLE:
		return "EEPROM Hole";
	case ATOM_EEPROM_PART:
		return "EEPROM Part #";
	// Informational Atoms
	case ATOM_INFO_SAMPLE_CODE:
		return "Sample Code";
	case ATOM_INFO_DOCS:
		return "Documentation";
#ifdef NDEBUG
	default:
		return "Unknown type";
#endif
	}
}

char* tofe_atom_print_string(char* ptr, const struct tofe_atomfmt_string* atom) {
	return strncpy(ptr, atom->str, atom->len);
}

char* tofe_atom_print_url(char* ptr, const struct tofe_atomfmt_url* atom) {
	ptr = stpcpy(ptr, "https://");
	return strncpy(ptr, atom->url, atom->len);
}

char* tofe_atom_print_relative_url(char* ptr, const struct tofe_atomfmt_relative_url* atom) {
	ptr = stpcpy(ptr, "https://");
	// ptr = tofe_atom_print_url(ptr, tofe_atom_get_url(hdr, atom->atom_index));
	ptr++ = '/';
	ptr = '\0';
	return strncpy(ptr, atom->rurl, atom->len - TOFE_EXTRA_LEN(atom));
}

char* tofe_atom_print_expand_int(char* ptr, const struct tofe_atomfmt_expand_int* atom) {
	__u32 value = 0;
	tofe_atomfmt_expand_int_get(atom, value);
	ptr += sprintf(ptr, "%d",  value);
	return ptr;
}

char* tofe_atom_print_license(char* ptr, const struct tofe_atomfmt_license* atom) {
	ptr = stpcpy(ptr, tofe_atomfmt_license_name(atom));
	ptr++ = ' ';
	ptr = '\0';
	ptr = stpcpy(ptr, tofe_atomfmt_license_version(atom));
	return ptr;
}

char* tofe_atom_print_size_offset(char* ptr, const struct tofe_atomfmt_size_offset* atom) {
	__u16 size = 0;
	__u16 offset = 0;
	
	tofe_atomfmt_size_offset_get_size(atom, size);
	tofe_atomfmt_size_offset_get_offset(atom, offset);

	ptr += sprintf("(%x->%x (%ib)", size, size+offset, offset);
	return ptr;
}

#define TOFE_ATOM_PRINT_CASE(name) \
	case ATOM_STYLE ## name : \
		return tofe_atom_print ## name (ptr, (const struct tofe_atomfmt ## name *)(atom))

char* tofe_atom_print(char* ptr, const struct tofe_atom* atom) {
	switch(tofe_atomfmt(atom)) {
	case ATOM_STYLE_invalid:
		return stpcpy(ptr, "??? (Invalid)");
	TOFE_ATOM_PRINT_CASE(string)
		;
	TOFE_ATOM_PRINT_CASE(url)
		;
	TOFE_ATOM_PRINT_CASE(relative_url)
		;
	TOFE_ATOM_PRINT_CASE(expand_int)
		;
	TOFE_ATOM_PRINT_CASE(license)
		;
	TOFE_ATOM_PRINT_CASE(size_offset)
		;
	TOFE_ATOM_PRINT_CASE(binary_blob)
		;
#ifdef NDEBUG
	default:
		return stpcpy(ptr, "??? (Unknown format)");
	}
#endif
}
