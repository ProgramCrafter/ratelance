

class JobNotifications {
    static const LOAD_URL = 'https://dton.io/graphql';
    static const LOAD_REQUEST = `
    {
      transactions(address_friendly: "EQA__RATELANCE_______________________________JvN") {
        gen_utime in_msg_src_addr_workchain_id in_msg_src_addr_address_hex in_msg_body
      }
    }
    `;
    
    static async load() {
        
    }
}