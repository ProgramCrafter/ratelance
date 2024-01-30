function TonAddressConvertor(hex){
    if(!hex) return '';
    hex = new TonWeb.utils.Address(hex);
    return hex.toString(true, true, true, false); // меняем вид 0: на нормальный
}

let wallets = document.getElementsByClassName('valid-number')

for(let i = 0; i < wallets.length; i++){
    let text = wallets[i].textContent.toString()
    text = TonAddressConvertor(text)

    wallets[i].href = `https://tonscan.org/address/${text}`
    wallets[i].target = '_blank'

    wallets[i].innerText = text.substring(0, 5) + '...' + text.substring(text.length-5, text.length)

}